#!/usr/bin/env python3
"""
Voice AI Orchestrator - main daemon.

State machine:
  IDLE -> (wake word detected) -> LISTENING -> (speech transcribed) ->
  THINKING -> (Claude streams response) -> SPEAKING -> IDLE

Trigger: "Hey Jarvis" wake word, or Super+Shift+V hotkey.
Brain: Claude via LiteLLM proxy (claude-haiku / claude-sonnet).
"""

import ctypes
import ctypes.util
import os
import subprocess
import sys
import tempfile
import threading
import time

import numpy as np
import pyaudio
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


# ── Interrupt detector ─────────────────────────────────────────────────

class InterruptDetector:
    """Listens for 'stop' commands while TTS is speaking.

    Runs a lightweight PyAudio energy detector in a background thread.
    When speech energy is detected, quickly Whisper-transcribes ~1.5s
    of audio and checks for stop words. If found, calls tts.stop().
    """

    STOP_WORDS = {
        "stop", "enough", "quiet", "silence", "cancel", "abort",
        "shut up", "never mind", "nevermind", "that's enough",
        "thats enough", "ok stop", "okay stop",
    }
    RMS_THRESHOLD = 600    # amplitude above which we consider it speech
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 1600      # 100ms of audio per chunk

    def __init__(self, tts, whisper_model):
        self.tts = tts
        self._whisper = whisper_model
        self._running = False
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Interrupt] Detector started.", flush=True)

    def stop(self):
        self._running = False

    def _loop(self):
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK_SIZE,
            )
            try:
                while self._running:
                    if not self.tts.is_speaking:
                        time.sleep(0.05)
                        continue

                    try:
                        chunk = stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
                    except Exception:
                        time.sleep(0.05)
                        continue

                    samples = np.frombuffer(chunk, dtype=np.int16).astype(np.float32)
                    rms = float(np.sqrt(np.mean(samples ** 2)))

                    if rms > self.RMS_THRESHOLD:
                        # Record ~1.5 more seconds
                        frames = [chunk]
                        for _ in range(15):  # 15 * 100ms = 1.5s
                            if not self.tts.is_speaking:
                                break
                            try:
                                frames.append(stream.read(self.CHUNK_SIZE, exception_on_overflow=False))
                            except Exception:
                                break

                        text = self._transcribe(b"".join(frames))
                        if text and self._is_stop(text):
                            print("[Interrupt] Stop command detected: '{}'".format(text), flush=True)
                            self.tts.stop()
            finally:
                stream.stop_stream()
                stream.close()
                pa.terminate()
        except Exception as e:
            print("[Interrupt] Detector error (non-fatal): {}".format(e), flush=True)

    def _transcribe(self, audio_bytes):
        """Quick Whisper transcription of raw PCM bytes."""
        if not self._whisper:
            return ""
        raw_path = None
        wav_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as f:
                f.write(audio_bytes)
                raw_path = f.name
            wav_path = raw_path + ".wav"
            subprocess.run(
                ["ffmpeg", "-f", "s16le", "-ar", "16000", "-ac", "1",
                 "-i", raw_path, wav_path, "-y", "-loglevel", "quiet"],
                timeout=3, check=False
            )
            if os.path.exists(wav_path):
                result = self._whisper.transcribe(wav_path, language="en", fp16=False)
                return result["text"].strip().lower()
        except Exception as e:
            print("[Interrupt] Transcribe error: {}".format(e), flush=True)
        finally:
            for p in [raw_path, wav_path]:
                if p:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass
        return ""

    def _is_stop(self, text):
        t = text.lower().strip(".,!?")
        return any(w in t for w in self.STOP_WORDS)


# ── Orchestrator ───────────────────────────────────────────────────────

class Orchestrator:
    def __init__(self):
        suppress_alsa()

        print("[Orchestrator] Initializing...", flush=True)

        # Core components — Brain first so we can pass its memory to FastRouter
        self.tts = TTS()
        self.task_router = TaskRouter()
        self.pane_monitor = PaneMonitor(poll_interval=3.0)
        self.brain = Brain(task_router=self.task_router, pane_monitor=self.pane_monitor)
        self.fast_router = FastRouter(self.task_router, memory=self.brain.memory)

        # Speaker verification
        self.speaker_verifier = SpeakerVerifier()

        # Voice input
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self._whisper_model = None

        # Interrupt detector (created after whisper load in run())
        self._interrupt_detector = None

        # Calibrate
        print("[Orchestrator] Calibrating microphone...", flush=True)
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 1.0
        self.recognizer.non_speaking_duration = 0.4

        # Wake word — triggers self._on_wake
        self.wake_detector = WakeWordDetector(on_wake=self._on_wake)

        # State
        self._active = False  # currently in a conversation turn

        # Pane monitor callbacks
        self.pane_monitor.on_state_change(self._on_pane_change)
        self._alerted = set()

        print("[Orchestrator] Ready.", flush=True)

    def _load_whisper(self):
        if self._whisper_model is None:
            print("[Orchestrator] Loading Whisper {}...".format(WHISPER_MODEL), flush=True)
            self._whisper_model = whisper.load_model(
                WHISPER_MODEL, download_root=WHISPER_MODELS_DIR
            )
            print("[Orchestrator] Whisper loaded.", flush=True)

    def _transcribe(self, audio):
        """Transcribe speech_recognition AudioData using Whisper."""
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

    def _on_wake(self, trailing_text=""):
        """Called when wake word is detected."""
        if self._active:
            self.tts.play_cached("busy")
            return
        self._active = True
        threading.Thread(target=self._conversation_turn, args=(trailing_text,), daemon=True).start()

    def _on_pane_change(self, window, old_state, new_state, snippet):
        """Called when a monitored pane changes state."""
        if old_state == PaneState.WORKING and new_state == PaneState.IDLE:
            key = (window, time.time() // 30)
            if key not in self._alerted:
                self._alerted.add(key)
                assignment = self.task_router.get_assignment(window)
                task_desc = assignment.prompt[:50] if assignment else "its task"
                self.task_router.mark_completed(window)
                msg = "Window {} has finished {}.".format(window, task_desc)
                print("[Orchestrator] {}".format(msg), flush=True)
                self._notify(msg)

        elif old_state == PaneState.WORKING and new_state == PaneState.ERRORED:
            key = (window, "error", time.time() // 60)
            if key not in self._alerted:
                self._alerted.add(key)
                self.task_router.mark_errored(window)
                msg = "Window {} encountered an error.".format(window)
                print("[Orchestrator] {}".format(msg), flush=True)
                self._notify(msg)

    def _notify(self, text):
        """Send desktop notification and speak via TTS."""
        try:
            subprocess.Popen(
                ["notify-send", "Jarvis", text],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except Exception:
            pass
        if not self._active:
            self.wake_detector.pause()
            self.tts.speak(text)
            self.wake_detector.resume()

    # ── Conversation classification ──────────────────────────────────────

    END_PHRASES = [
        "end conversation", "stop conversation", "goodbye", "bye",
        "jarvis end", "jarvis stop", "that's all", "thats all",
        "never mind", "nevermind", "dismiss",
    ]

    ACTION_KEYWORDS = {
        "click", "type", "open", "mouse", "screen", "browser", "window",
        "scroll", "fill", "form", "cursor", "move", "press", "close",
        "focus", "switch", "tab", "desktop", "display", "launch", "run",
    }

    @staticmethod
    def _classify_complexity(text):
        """'quick' for short/simple queries; 'full' for screen/action tasks."""
        words = text.lower().split()
        if any(w in Orchestrator.ACTION_KEYWORDS for w in words):
            return "full"
        if len(words) <= 12:
            return "quick"
        return "full"

    def _is_end_command(self, text):
        t = text.lower().strip().strip(".,!?")
        return any(phrase in t for phrase in self.END_PHRASES)

    # ── Conversation loop ────────────────────────────────────────────────

    def _conversation_turn(self, wake_text=""):
        """Multi-turn conversation loop. Streams Claude responses sentence-by-sentence."""
        try:
            self.wake_detector.pause()

            while True:
                user_text = self._listen_for_command()

                if not user_text or len(user_text.strip()) < 2:
                    continue

                if self._is_end_command(user_text):
                    print("[Orchestrator] End command: '{}'".format(user_text), flush=True)
                    self.tts.speak("Alright, talk to you later.")
                    break

                # Fast local routing first — no LLM needed
                fast_result = self.fast_router.try_route(user_text)
                if fast_result:
                    action, response = fast_result
                    print("[Orchestrator] Fast route ({}): {}".format(action, response), flush=True)
                    self.tts.speak(response)
                else:
                    complexity = self._classify_complexity(user_text)
                    print("[Orchestrator] Thinking (Claude, {})...".format(complexity), flush=True)

                    # Stream sentences directly into TTS
                    sentence_gen = self.brain.think_streaming(user_text, mode=complexity)
                    self.tts.speak_streaming(sentence_gen)

        except Exception as e:
            print("[Orchestrator] Error in conversation: {}".format(e), flush=True)
            self.tts.play_cached("error")
        finally:
            self._active = False
            self.brain.reset()  # saves summary to memory, clears history
            self.wake_detector.resume()
            print("[Orchestrator] Conversation ended, wake word listening resumed.", flush=True)

    def _listen_for_command(self):
        """Listen and transcribe user speech. Retries once on empty result."""
        for attempt in range(2):
            if attempt > 0:
                print("[Orchestrator] Retrying listen...", flush=True)

            print("[Orchestrator] Listening...", flush=True)
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

            if self.speaker_verifier.is_enrolled():
                is_match, score = self.speaker_verifier.verify(audio)
                if not is_match:
                    print("[Orchestrator] Speaker rejected (similarity={:.3f})".format(score), flush=True)
                    return ""
                print("[Orchestrator] Speaker verified (similarity={:.3f})".format(score), flush=True)

            print("[Orchestrator] Transcribing...", flush=True)
            text = self._transcribe(audio)
            print("[Orchestrator] User: {}".format(text), flush=True)

            if text and len(text.strip()) >= 2:
                return text

        return ""

    def _watch_signal_file(self):
        """Watch for hotkey trigger file (Super+Shift+V)."""
        while True:
            if os.path.exists(SIGNAL_FILE):
                try:
                    os.remove(SIGNAL_FILE)
                except OSError:
                    pass
                self._on_wake("")
            time.sleep(0.1)

    def run(self):
        """Start the orchestrator daemon."""
        print("[Orchestrator] Starting up...", flush=True)
        print("  Wake word:  'Hey Jarvis'", flush=True)
        print("  Hotkey:     touch {}".format(SIGNAL_FILE), flush=True)
        print("  TTS voice:  {}".format(self.tts.voice), flush=True)
        print("  Brain:      Claude via LiteLLM ({}:{})".format(
            "haiku", "sonnet"), flush=True)
        print("  Memory:     Session #{}".format(self.brain.memory.session_count), flush=True)
        print("", flush=True)

        # Load Whisper, cache TTS phrases
        self._load_whisper()
        self.tts.precache()

        # Start interrupt detector now that Whisper is loaded
        self._interrupt_detector = InterruptDetector(self.tts, self._whisper_model)
        self._interrupt_detector.start()

        # Auto-watch existing tmux windows
        try:
            r = subprocess.run(
                ["tmux", "list-windows", "-F", "#{window_index}"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    try:
                        self.pane_monitor.watch(int(line.strip()))
                    except ValueError:
                        pass
        except Exception:
            pass
        self.pane_monitor.start()

        # Signal file watcher thread (hotkey support)
        threading.Thread(target=self._watch_signal_file, daemon=True).start()

        # Wake word detection
        self.wake_detector.start()
        print("[Orchestrator] Running. Say 'Hey Jarvis' or press Super+Shift+V.", flush=True)

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Orchestrator] Shutting down...", flush=True)
            if self._interrupt_detector:
                self._interrupt_detector.stop()
            self.wake_detector.stop()
            self.pane_monitor.stop()


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()
