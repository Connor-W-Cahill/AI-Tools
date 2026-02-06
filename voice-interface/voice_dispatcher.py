#!/usr/bin/env python3
"""
Voice Dispatcher - Say a number to switch tmux windows and dictate to AI.

Flow:
  1. Super+Shift+V triggers listening
  2. Say a number → switches to that tmux window
  3. Streams live transcription (tiny.en) to tmux status bar
  4. Say "send" to immediately send, or pause to end
  5. Final re-transcription with small.en for accuracy before sending

Uses local Whisper for offline speech-to-text.
"""

import io
import os
import re
import struct
import subprocess
import tempfile
import threading
import time
import wave
import ctypes
import ctypes.util

import speech_recognition as sr
import whisper

# ── Config ──────────────────────────────────────────────────────────────

WHISPER_MODEL_FAST = "tiny.en"      # live streaming preview (speed)
WHISPER_MODEL_ACCURATE = "small.en"  # final transcription (accuracy)
WHISPER_MODELS_DIR = os.path.expanduser("~/.claude/mcp-servers/whisper-voice/models")
LISTEN_TIMEOUT = 6
SILENCE_TIMEOUT = 3.0
CHUNK_DURATION = 3
MAX_PROMPT_SECONDS = 90
NUMBER_PHRASE_LIMIT = 4
SEND_PHRASES = ["send", "send it", "submit", "sent", "san", "scend"]
STOP_PHRASES = ["stop", "cancel", "never mind", "nevermind", "abort"]
WAIT_PHRASES = ["wait", "hold on", "pause"]
CLEAR_PHRASES = ["clear", "clear it", "start over", "erase"]
TRANSCRIBE_PHRASES = ["transcribe", "type", "type it", "transcribed"]
SIGNAL_FILE = "/tmp/voice_dispatch_trigger"

WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "to": 2, "too": 2,
    "three": 3, "four": 4, "for": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "ate": 8,
    "nine": 9, "ten": 10,
}

# ── ALSA suppression ───────────────────────────────────────────────────

_alsa_error_handler = None

def suppress_alsa_errors():
    global _alsa_error_handler
    try:
        asound = ctypes.cdll.LoadLibrary(ctypes.util.find_library("asound") or "libasound.so.2")
        c_type = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int,
                                  ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
        def _null(f, l, fn, e, fmt):
            pass
        _alsa_error_handler = c_type(_null)
        asound.snd_lib_error_set_handler(_alsa_error_handler)
    except Exception:
        pass


# ── Helpers ─────────────────────────────────────────────────────────────

def beep():
    try:
        for s in ["/usr/share/sounds/freedesktop/stereo/message-new-instant.oga",
                  "/usr/share/sounds/freedesktop/stereo/bell.oga",
                  "/usr/share/sounds/gnome/default/alerts/drip.ogg"]:
            if os.path.exists(s):
                subprocess.Popen(["paplay", s], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
    except Exception:
        pass


def parse_window_number(text):
    text = text.strip()
    words = text.split()
    if not words:
        return None, text
    first = words[0].lower().strip(".,!?")
    if first.isdigit():
        return int(first), " ".join(words[1:]).strip()
    if first in WORD_TO_NUM:
        return WORD_TO_NUM[first], " ".join(words[1:]).strip()
    return None, text


def is_noise(text):
    cleaned = text.strip().strip(".").strip()
    if not cleaned:
        return True
    if cleaned.startswith("(") and cleaned.endswith(")"):
        return True
    return False


def check_phrase(text, phrases):
    """Check if any phrase appears in text. Returns (found, text_without_phrase)."""
    lower = text.lower()
    for p in phrases:
        if p in lower:
            cleaned = re.sub(re.escape(p), "", text, flags=re.IGNORECASE).strip()
            return True, cleaned
    return False, text


FILLER_WORDS = {"okay", "ok", "please", "now", "it", "the", "um", "uh", "so",
                "hey", "just", "go", "do", "that", "this", "yeah", "yep", "alright",
                "a", "an", "and", "i", "you", "we", "my", "me", "oh", "ah",
                "right", "like", "well", "then", "can", "could", "would"}

def is_command_only(text, phrases):
    """
    Check if the chunk is essentially just a command with optional filler.
    Two paths:
      1. Short utterance (≤3 words total) containing a command → always a command
      2. Longer utterance → at most 1 non-filler word may remain after removing command
    This still prevents "send it to the server" from triggering "send".
    """
    found, remainder = check_phrase(text, phrases)
    if not found:
        return False, text

    # Short utterance fast path: if the whole text is ≤3 words, it's a command
    all_words = [w for w in text.strip().split() if w.strip(".,!?")]
    if len(all_words) <= 3:
        return True, remainder

    # Longer utterance: allow at most 1 non-filler leftover word
    leftover_words = [w for w in remainder.lower().strip(".,!?").split()
                      if w.strip(".,!?") not in FILLER_WORDS and w.strip(".,!?")]
    if len(leftover_words) > 1:
        return False, text  # too many meaningful words left → not a command
    return True, remainder


def concat_audio(audio_chunks):
    """Concatenate multiple sr.AudioData objects into one WAV file path."""
    if not audio_chunks:
        return None

    # Get params from first chunk
    sample_rate = audio_chunks[0].sample_rate
    sample_width = audio_chunks[0].sample_width

    # Combine raw PCM data
    combined = b""
    for chunk in audio_chunks:
        combined += chunk.get_raw_data()

    # Write as WAV
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(tmp.name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(combined)
    return tmp.name


# ── tmux status bar ─────────────────────────────────────────────────────

_original_status_right = None
_original_status_style = None
_original_status_len = None

def tmux_status_show(text, style="bg=blue,fg=white,bold"):
    global _original_status_right, _original_status_style, _original_status_len
    try:
        if _original_status_right is None:
            r = subprocess.run(["tmux", "show-option", "-gv", "status-right"],
                               capture_output=True, text=True)
            _original_status_right = r.stdout.strip() if r.returncode == 0 else ""
            r = subprocess.run(["tmux", "show-option", "-gv", "status-right-style"],
                               capture_output=True, text=True)
            _original_status_style = r.stdout.strip() if r.returncode == 0 else ""
            r = subprocess.run(["tmux", "show-option", "-gv", "status-right-length"],
                               capture_output=True, text=True)
            _original_status_len = r.stdout.strip() if r.returncode == 0 else "40"

        display = text[:80] if len(text) > 80 else text
        subprocess.run(["tmux", "set-option", "-g", "status-right", f" {display} "],
                       capture_output=True, text=True)
        subprocess.run(["tmux", "set-option", "-g", "status-right-style", style],
                       capture_output=True, text=True)
        subprocess.run(["tmux", "set-option", "-g", "status-right-length", "85"],
                       capture_output=True, text=True)
    except Exception:
        pass


def tmux_status_restore():
    global _original_status_right, _original_status_style, _original_status_len
    try:
        if _original_status_right is not None:
            subprocess.run(["tmux", "set-option", "-g", "status-right", _original_status_right],
                           capture_output=True, text=True)
        if _original_status_style is not None:
            subprocess.run(["tmux", "set-option", "-g", "status-right-style", _original_status_style],
                           capture_output=True, text=True)
        if _original_status_len is not None:
            subprocess.run(["tmux", "set-option", "-g", "status-right-length", _original_status_len],
                           capture_output=True, text=True)
        _original_status_right = None
        _original_status_style = None
        _original_status_len = None
    except Exception:
        pass


# ── Core ────────────────────────────────────────────────────────────────

class VoiceDispatcher:
    def __init__(self):
        suppress_alsa_errors()
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.models = {}
        self.active = False

        print("Calibrating microphone...", flush=True)
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=2)
        # Tune recognizer for noisy environments
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.pause_threshold = 1.0
        self.recognizer.non_speaking_duration = 0.5
        print("Microphone ready.", flush=True)

    def load_model(self, name):
        if name not in self.models:
            print(f"Loading Whisper model '{name}'...", flush=True)
            self.models[name] = whisper.load_model(name, download_root=WHISPER_MODELS_DIR)
            print(f"Model '{name}' loaded.", flush=True)
        return self.models[name]

    def transcribe(self, audio_data, model_name=WHISPER_MODEL_FAST):
        model = self.load_model(model_name)
        wav_bytes = audio_data.get_wav_data()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp = f.name
        try:
            result = model.transcribe(tmp, language="en", fp16=False)
            return result["text"].strip()
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def transcribe_file(self, wav_path, model_name=WHISPER_MODEL_ACCURATE):
        """Transcribe a WAV file with a specific model."""
        model = self.load_model(model_name)
        result = model.transcribe(wav_path, language="en", fp16=False)
        return result["text"].strip()

    def record_chunk(self, timeout=None, phrase_limit=None):
        """Record a single audio chunk. Returns (AudioData, quick_text) or (None, None)."""
        timeout = timeout or LISTEN_TIMEOUT
        phrase_limit = phrase_limit or CHUNK_DURATION
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=timeout,
                                               phrase_time_limit=phrase_limit)
            # Quick transcription with fast model for live display
            quick_text = self.transcribe(audio, WHISPER_MODEL_FAST)
            return audio, quick_text
        except sr.WaitTimeoutError:
            return None, None

    def listen_streaming(self, window_num, max_seconds=MAX_PROMPT_SECONDS, first_timeout=8):
        """
        Stream-transcribe in 2s chunks.
        - Shows live text (tiny.en) in tmux status bar
        - "send" finishes + submits; "transcribe" finishes without submit
        - "stop"/"cancel" aborts; "wait" pauses; "clear" wipes
        Returns (final_text, action) where action is 'send'|'transcribe'|'cancel'|'empty'.
        """
        preview_parts = []
        audio_chunks = []
        max_chunks = max_seconds // CHUNK_DURATION
        silence_streak = 0
        PATIENCE = 4  # allow up to 4 consecutive silence timeouts before giving up
        action = "empty"

        for i in range(max_chunks):
            timeout = first_timeout if i == 0 or not audio_chunks else 5
            audio, text = self.record_chunk(timeout=timeout, phrase_limit=CHUNK_DURATION)

            if audio is None:
                silence_streak += 1
                if silence_streak >= PATIENCE:
                    print("  No speech for too long, giving up.", flush=True)
                    return "", "empty"
                continue
            silence_streak = 0

            if text is None or is_noise(text):
                continue

            # ── Commands (checked on short utterances only to avoid false triggers) ──

            # Cancel — any length
            is_cancel, _ = check_phrase(text, STOP_PHRASES)
            if is_cancel:
                print("  Cancelled.", flush=True)
                return "", "cancel"

            # Clear — short only. Also clear the pane input.
            is_clear, _ = is_command_only(text, CLEAR_PHRASES)
            if is_clear:
                preview_parts.clear()
                audio_chunks.clear()
                # Send Ctrl+C to the pane to clear its input line
                subprocess.run(["tmux", "send-keys", "-t", str(window_num), "C-c"],
                               capture_output=True, text=True)
                tmux_status_show("MIC: cleared - speak again...", "bg=yellow,fg=black,bold")
                print("  Cleared.", flush=True)
                beep()
                continue

            # Wait — short only
            is_wait, _ = is_command_only(text, WAIT_PHRASES)
            if is_wait:
                current = " ".join(preview_parts) if preview_parts else "(empty)"
                tmux_status_show(f"PAUSED: {current}  [speak to continue]",
                                 "bg=yellow,fg=black,bold")
                print(f"  Paused. Current: {current}", flush=True)
                continue

            # Send — short only
            is_send, cleaned = is_command_only(text, SEND_PHRASES)
            if is_send:
                if cleaned:
                    preview_parts.append(cleaned)
                    audio_chunks.append(audio)
                action = "send"
                print("  Send triggered.", flush=True)
                break

            # Transcribe — short only. Paste current text, keep listening.
            is_transcribe, cleaned = is_command_only(text, TRANSCRIBE_PHRASES)
            if is_transcribe:
                if cleaned:
                    preview_parts.append(cleaned)
                    audio_chunks.append(audio)
                if audio_chunks:
                    # Do the accurate pass and paste now
                    tmux_status_show("MIC: refining...", "bg=cyan,fg=black,bold")
                    wav_path = concat_audio(audio_chunks)
                    if wav_path:
                        try:
                            pasted_text = self.transcribe_file(wav_path, WHISPER_MODEL_ACCURATE)
                        finally:
                            try:
                                os.unlink(wav_path)
                            except OSError:
                                pass
                    else:
                        pasted_text = " ".join(preview_parts).strip()
                    # Paste into pane without Enter
                    subprocess.run(["tmux", "set-buffer", pasted_text],
                                   capture_output=True, text=True)
                    subprocess.run(["tmux", "paste-buffer", "-t", str(window_num)],
                                   capture_output=True, text=True)
                    tmux_status_show(f"TYPED: {pasted_text}  [send|clear|cancel]",
                                     "bg=blue,fg=white,bold")
                    print(f"  Transcribed to pane: {pasted_text}", flush=True)
                    # Reset — text is in the pane now, fresh accumulator
                    preview_parts.clear()
                    audio_chunks.clear()
                    beep()
                continue

            # ── Normal speech ──
            preview_parts.append(text)
            audio_chunks.append(audio)

            current = " ".join(preview_parts)
            tmux_status_show(f"MIC: {current}")
            print(f"  [{i}] {text}", flush=True)

        if not audio_chunks:
            return "", "empty"

        # ── Final accurate pass with base.en ──
        tmux_status_show("MIC: refining...", "bg=cyan,fg=black,bold")
        print("  Re-transcribing with small.en...", flush=True)

        wav_path = concat_audio(audio_chunks)
        if wav_path:
            try:
                final_text = self.transcribe_file(wav_path, WHISPER_MODEL_ACCURATE)
                print(f"  Final: {final_text}", flush=True)
                return final_text, action
            finally:
                try:
                    os.unlink(wav_path)
                except OSError:
                    pass

        return " ".join(preview_parts).strip(), action

    def dispatch(self):
        if self.active:
            return
        self.active = True

        try:
            # ── Phase 1: Window number ──
            tmux_status_show("MIC: say a window number...", "bg=magenta,fg=white,bold")
            beep()
            print("\nListening for window number...", flush=True)

            _, text = self.record_chunk(timeout=LISTEN_TIMEOUT, phrase_limit=NUMBER_PHRASE_LIMIT)
            if not text:
                print("No speech detected.", flush=True)
                tmux_status_restore()
                return

            print(f"Heard: {text}", flush=True)
            window_num, remaining = parse_window_number(text)

            if window_num is None:
                tmux_status_show(f"MIC: '{text}' not a number", "bg=red,fg=white,bold")
                print(f"Couldn't parse window number from: {text}", flush=True)
                time.sleep(1.5)
                tmux_status_restore()
                return

            # Switch tmux window
            r = subprocess.run(["tmux", "select-window", "-t", str(window_num)],
                               capture_output=True, text=True)
            if r.returncode != 0:
                tmux_status_show(f"MIC: window {window_num} not found", "bg=red,fg=white,bold")
                print(f"tmux window {window_num} not found.", flush=True)
                time.sleep(1.5)
                tmux_status_restore()
                return

            print(f"-> Window {window_num}", flush=True)

            # ── Phase 2: Stream the prompt ──
            tmux_status_show(f"MIC: window {window_num} - send|wait|clear|stop",
                             "bg=green,fg=black,bold")
            beep()
            time.sleep(0.1)
            beep()

            if remaining:
                tmux_status_show(f"MIC: {remaining}")

            prompt, action = self.listen_streaming(
                window_num,
                first_timeout=5 if remaining else 8
            )

            if remaining and prompt:
                prompt = remaining + " " + prompt
            elif remaining and not prompt and action != "cancel":
                prompt = remaining

            if action == "cancel":
                tmux_status_show("MIC: cancelled", "bg=red,fg=white,bold")
                time.sleep(1)
                tmux_status_restore()
                return

            if action == "send" and not prompt:
                # "send" after a transcribe — text is already in the pane, just Enter
                time.sleep(0.1)
                subprocess.run(
                    ["tmux", "send-keys", "-t", str(window_num), "Enter"],
                    capture_output=True, text=True
                )
                tmux_status_show("SENT (submitted)", "bg=green,fg=black,bold")
                print(f"Submitted pane input on window {window_num}", flush=True)
                time.sleep(2)
                tmux_status_restore()
                return

            if not prompt:
                tmux_status_show(f"-> window {window_num} (no prompt)", "bg=yellow,fg=black")
                print("Switched window (no prompt).", flush=True)
                time.sleep(1)
                tmux_status_restore()
                return

            if action == "send":
                # Paste text + submit
                subprocess.run(["tmux", "set-buffer", prompt],
                               capture_output=True, text=True)
                subprocess.run(["tmux", "paste-buffer", "-t", str(window_num)],
                               capture_output=True, text=True)
                time.sleep(0.1)
                subprocess.run(
                    ["tmux", "send-keys", "-t", str(window_num), "Enter"],
                    capture_output=True, text=True
                )
                tmux_status_show(f"SENT: {prompt}", "bg=green,fg=black,bold")
                print(f"Sent to window {window_num}", flush=True)
            else:
                # Ended without explicit send — paste without submitting
                subprocess.run(["tmux", "set-buffer", prompt],
                               capture_output=True, text=True)
                subprocess.run(["tmux", "paste-buffer", "-t", str(window_num)],
                               capture_output=True, text=True)
                tmux_status_show(f"TYPED: {prompt}", "bg=blue,fg=white,bold")
                print(f"Typed to window {window_num} (not sent)", flush=True)

            time.sleep(2)
            tmux_status_restore()

        except Exception as e:
            print(f"Error: {e}", flush=True)
            tmux_status_restore()
        finally:
            self.active = False

    def watch_signal_file(self):
        while True:
            if os.path.exists(SIGNAL_FILE):
                try:
                    os.remove(SIGNAL_FILE)
                except OSError:
                    pass
                self.dispatch()
            time.sleep(0.1)

    def run(self):
        print("Voice Dispatcher starting...", flush=True)
        print(f"  Fast model: {WHISPER_MODEL_FAST} (live preview)", flush=True)
        print(f"  Accurate model: {WHISPER_MODEL_ACCURATE} (final pass)", flush=True)
        print(f"  Trigger: Super+Shift+V or touch {SIGNAL_FILE}", flush=True)
        print(f"  Chunk: {CHUNK_DURATION}s", flush=True)
        print(f"  Say 'send' to send | 'stop'/'cancel' to abort", flush=True)
        print("", flush=True)

        self.load_model(WHISPER_MODEL_FAST)
        self.load_model(WHISPER_MODEL_ACCURATE)

        print("Ready. Waiting for hotkey...", flush=True)

        watcher = threading.Thread(target=self.watch_signal_file, daemon=True)
        watcher.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down.", flush=True)


if __name__ == "__main__":
    dispatcher = VoiceDispatcher()
    dispatcher.run()
