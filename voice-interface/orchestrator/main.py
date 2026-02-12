#!/usr/bin/env python3
"""
Voice AI Orchestrator - main daemon.

State machine:
  IDLE → (wake word detected) → LISTENING → (speech transcribed) →
  THINKING → (Claude responds) → SPEAKING → IDLE

Trigger: "Hey Claude" / "Claude" wake word, or Super+Shift+V hotkey.
"""

import ctypes
import ctypes.util
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time

import speech_recognition as sr
import whisper

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tts import TTS
from wake_word import WakeWordDetector
from brain import Brain
from fast_router import FastRouter
from pane_monitor import PaneMonitor, PaneState
from task_router import TaskRouter
from speaker_verify import SpeakerVerifier

# ── Config ──────────────────────────────────────────────────────────────

WHISPER_MODEL = "base.en"
WHISPER_MODELS_DIR = os.path.expanduser("~/.claude/mcp-servers/whisper-voice/models")
SIGNAL_FILE = "/tmp/voice_orchestrator_trigger"
LISTEN_TIMEOUT = 5
PHRASE_LIMIT = 15  # max seconds per voice input

# ── ALSA suppression ───────────────────────────────────────────────────

_alsa_handler = None
def suppress_alsa():
    global _alsa_handler
    try:
        asound = ctypes.cdll.LoadLibrary(ctypes.util.find_library("asound") or "libasound.so.2")
        c_type = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int,
                                  ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
        _alsa_handler = c_type(lambda *a: None)
        asound.snd_lib_error_set_handler(_alsa_handler)
    except Exception:
        pass


# ── Orchestrator ───────────────────────────────────────────────────────

class Orchestrator:
    def __init__(self):
        suppress_alsa()

        print("[Orchestrator] Initializing...", flush=True)

        # Components
        self.tts = TTS()
        self.task_router = TaskRouter()
        self.fast_router = FastRouter(self.task_router)
        self.pane_monitor = PaneMonitor(poll_interval=3.0)
        self.brain = Brain(task_router=self.task_router, pane_monitor=self.pane_monitor)

        # Speaker verification
        self.speaker_verifier = SpeakerVerifier()

        # Voice input
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self._whisper_model = None

        # Calibrate
        print("[Orchestrator] Calibrating microphone...", flush=True)
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0
        self.recognizer.non_speaking_duration = 0.4

        # Wake word — triggers self._on_wake with trailing text
        self.wake_detector = WakeWordDetector(on_wake=self._on_wake)

        # State
        self._active = False  # currently in a conversation turn

        # Set up pane monitor callbacks
        self.pane_monitor.on_state_change(self._on_pane_change)

        # Track which windows we've already alerted about
        self._alerted: set = set()

        print("[Orchestrator] Ready.", flush=True)

    def _load_whisper(self):
        if self._whisper_model is None:
            print(f"[Orchestrator] Loading Whisper {WHISPER_MODEL}...", flush=True)
            self._whisper_model = whisper.load_model(WHISPER_MODEL, download_root=WHISPER_MODELS_DIR)
            print("[Orchestrator] Whisper loaded.", flush=True)

    def _transcribe(self, audio: sr.AudioData) -> str:
        """Transcribe audio with base.en for speed + accuracy balance."""
        self._load_whisper()
        wav_bytes = audio.get_wav_data()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp = f.name
        try:
            result = self._whisper_model.transcribe(tmp, language="en", fp16=False)
            return result["text"].strip()
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def _on_wake(self, trailing_text: str = ""):
        """Called when wake word is detected. trailing_text has any command after the wake phrase."""
        if self._active:
            # Already busy — acknowledge so user knows we heard them
            self.tts.play_cached("busy")
            return
        self._active = True
        threading.Thread(target=self._conversation_turn, args=(trailing_text,), daemon=True).start()

    def _on_pane_change(self, window: int, old_state: PaneState, new_state: PaneState, snippet: str):
        """Called when a monitored pane changes state."""
        if old_state == PaneState.WORKING and new_state == PaneState.IDLE:
            key = (window, time.time() // 30)
            if key not in self._alerted:
                self._alerted.add(key)
                assignment = self.task_router.get_assignment(window)
                task_desc = assignment.prompt[:50] if assignment else "its task"
                self.task_router.mark_completed(window)
                msg = f"Window {window} has finished {task_desc}."
                print(f"[Orchestrator] {msg}", flush=True)
                self._notify(msg)

        # Only alert errors when a task was actively running — avoids false positives
        # from normal terminal output containing error-like words
        elif old_state == PaneState.WORKING and new_state == PaneState.ERRORED:
            key = (window, "error", time.time() // 60)
            if key not in self._alerted:
                self._alerted.add(key)
                self.task_router.mark_errored(window)
                msg = f"Window {window} encountered an error."
                print(f"[Orchestrator] {msg}", flush=True)
                self._notify(msg)

    def _notify(self, text: str):
        """Send notification via TTS and desktop notification."""
        try:
            subprocess.Popen(
                ["notify-send", "AI Orchestrator", text],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass
        if not self._active:
            self.wake_detector.pause()
            self.tts.speak(text)
            self.wake_detector.resume()

    # Phrases that end the conversation
    END_PHRASES = ["end conversation", "stop conversation", "goodbye", "bye",
                   "jarvis end", "jarvis stop", "that's all", "thats all",
                   "never mind", "nevermind", "dismiss"]

    # Keywords that indicate a complex/screen request requiring full context
    ACTION_KEYWORDS = {"click", "type", "open", "mouse", "screen", "browser", "window",
                       "scroll", "fill", "form", "cursor", "move", "press", "close",
                       "focus", "switch", "tab", "desktop", "display", "launch", "run"}

    @staticmethod
    def _classify_complexity(text: str) -> str:
        """Classify whether a request needs full screen context or a quick answer."""
        words = text.lower().split()
        if any(w in Orchestrator.ACTION_KEYWORDS for w in words):
            return "full"
        if len(words) <= 12:
            return "quick"
        return "full"

    def _is_end_command(self, text: str) -> bool:
        """Check if the user wants to end the conversation."""
        t = text.lower().strip().strip(".,!?")
        return any(phrase in t for phrase in self.END_PHRASES)

    def _conversation_turn(self, wake_text: str = ""):
        """Multi-turn conversation loop. Keeps listening until user says end or silence timeout."""
        try:
            self.wake_detector.pause()

            while True:
                user_text = self._listen_for_command()

                if not user_text or len(user_text.strip()) < 2:
                    continue

                # Check for end command
                if self._is_end_command(user_text):
                    print(f"[Orchestrator] End command: '{user_text}'", flush=True)
                    self.tts.speak("Alright, talk to you later.")
                    break

                # Try fast local routing first (instant, no thinking needed)
                fast_result = self.fast_router.try_route(user_text)
                if fast_result:
                    action, response = fast_result
                    print(f"[Orchestrator] Fast route ({action}): {response}", flush=True)
                    self.tts.speak(response)
                else:
                    complexity = self._classify_complexity(user_text)
                    print(f"[Orchestrator] Thinking (Codex, {complexity})...", flush=True)
                    response = self.brain.think(user_text, mode=complexity)
                    print(f"[Orchestrator] Response: {response}", flush=True)
                    if response:
                        self.tts.speak(response)

        except Exception as e:
            print(f"[Orchestrator] Error in conversation: {e}", flush=True)
            self.tts.play_cached("error")
        finally:
            self._active = False
            self.brain.reset()  # clear conversation memory between sessions
            self.wake_detector.resume()
            print("[Orchestrator] Conversation ended, wake word listening resumed.", flush=True)

    def _listen_for_command(self) -> str:
        """Listen and transcribe user speech. Retries once on empty result."""
        for attempt in range(2):
            if attempt > 0:
                print("[Orchestrator] Retrying listen...", flush=True)

            print("[Orchestrator] Listening for prompt...", flush=True)
            try:
                with self.microphone as source:
                    audio = self.recognizer.listen(
                        source, timeout=LISTEN_TIMEOUT, phrase_time_limit=PHRASE_LIMIT
                    )
            except sr.WaitTimeoutError:
                print("[Orchestrator] No speech detected.", flush=True)
                if attempt == 0:
                    continue
                return ""

            # Speaker verification — reject non-matching audio before transcription
            if self.speaker_verifier.is_enrolled():
                is_match, score = self.speaker_verifier.verify(audio)
                if not is_match:
                    print(f"[Orchestrator] Speaker rejected (similarity={score:.3f})", flush=True)
                    return ""
                print(f"[Orchestrator] Speaker verified (similarity={score:.3f})", flush=True)

            print("[Orchestrator] Transcribing...", flush=True)
            text = self._transcribe(audio)
            print(f"[Orchestrator] User: {text}", flush=True)

            if text and len(text.strip()) >= 2:
                return text

        return ""

    def _watch_signal_file(self):
        """Watch for trigger file (from hotkey)."""
        while True:
            if os.path.exists(SIGNAL_FILE):
                try:
                    os.remove(SIGNAL_FILE)
                except OSError:
                    pass
                self._on_wake("")
            time.sleep(0.1)

    def run(self):
        """Start the orchestrator."""
        print("[Orchestrator] Starting up...", flush=True)
        print(f"  Wake word: 'Hey Jarvis'", flush=True)
        print(f"  Hotkey trigger: touch {SIGNAL_FILE}", flush=True)
        print(f"  TTS voice: {self.tts.voice}", flush=True)
        print(f"  Fast router: enabled (simple commands bypass Codex)", flush=True)
        print("", flush=True)

        # Pre-load Whisper and cache TTS phrases
        self._load_whisper()
        self.tts.precache()

        # Start monitoring tmux windows
        try:
            r = subprocess.run(
                ["tmux", "list-windows", "-F", "#{window_index}"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    try:
                        idx = int(line.strip())
                        self.pane_monitor.watch(idx)
                    except ValueError:
                        pass
        except Exception:
            pass
        self.pane_monitor.start()

        # Start signal file watcher
        signal_thread = threading.Thread(target=self._watch_signal_file, daemon=True)
        signal_thread.start()

        # Start wake word detection
        self.wake_detector.start()
        print("[Orchestrator] Running. Say 'Hey Claude' or press hotkey.", flush=True)

        # Keep alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Orchestrator] Shutting down...", flush=True)
            self.wake_detector.stop()
            self.pane_monitor.stop()


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()
