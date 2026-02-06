"""
Wake word detection using openwakeword with "hey jarvis" model.

Processes continuous 80ms audio chunks with no gaps — far more reliable
than the previous Whisper-based approach which missed speech during transcription.
"""

import ctypes
import ctypes.util
import collections
import os
import struct
import threading
import time
from typing import Callable, Optional

import numpy as np
import pyaudio
from openwakeword.model import Model as OWWModel

# Suppress ALSA warnings
def _suppress_alsa():
    try:
        asound = ctypes.cdll.LoadLibrary(ctypes.util.find_library("asound") or "libasound.so.2")
        c_type = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int,
                                  ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
        handler = c_type(lambda *a: None)
        asound.snd_lib_error_set_handler(handler)
        return handler  # prevent GC
    except Exception:
        return None

_alsa_handler = _suppress_alsa()

# Wake word config
WAKE_MODEL = "hey_jarvis_v0.1"
THRESHOLD = 0.35      # confidence threshold (0-1) — lower = more sensitive
COOLDOWN = 2.0        # seconds between activations
SAMPLE_RATE = 16000
CHUNK_SAMPLES = 1280  # 80ms at 16kHz — what openwakeword expects


class WakeWordDetector:
    def __init__(self, on_wake: Optional[Callable[[str], None]] = None):
        """on_wake receives empty string (openwakeword doesn't transcribe)."""
        self.on_wake = on_wake
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._last_activation = 0.0
        self._model: Optional[OWWModel] = None
        self._audio: Optional[pyaudio.PyAudio] = None
        self._stream = None

    def _load_model(self):
        if self._model is None:
            print(f"[WakeWord] Loading openwakeword ({WAKE_MODEL})...", flush=True)
            self._model = OWWModel(wakeword_models=[WAKE_MODEL])
            print("[WakeWord] Model loaded.", flush=True)

    def _open_stream(self):
        if self._audio is None:
            self._audio = pyaudio.PyAudio()
        if self._stream is None or not self._stream.is_active():
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SAMPLES,
            )

    def _close_stream(self):
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._audio:
            try:
                self._audio.terminate()
            except Exception:
                pass
            self._audio = None

    def _listen_loop(self):
        """Continuous audio processing — no gaps."""
        self._load_model()
        self._open_stream()
        print("[WakeWord] Listening for 'Hey Jarvis'...", flush=True)

        while self._running:
            if self._paused:
                time.sleep(0.05)
                continue

            try:
                audio_bytes = self._stream.read(CHUNK_SAMPLES, exception_on_overflow=False)
                audio_np = np.frombuffer(audio_bytes, dtype=np.int16)

                prediction = self._model.predict(audio_np)
                score = prediction.get(WAKE_MODEL, 0.0)

                if score >= THRESHOLD:
                    now = time.time()
                    if now - self._last_activation >= COOLDOWN:
                        self._last_activation = now
                        print(f"[WakeWord] Detected! (score={score:.2f})", flush=True)
                        # Reset model state to avoid repeat triggers
                        self._model.reset()
                        if self.on_wake:
                            self.on_wake("")

            except IOError:
                # Audio buffer overflow — skip
                continue
            except Exception as e:
                print(f"[WakeWord] Error: {e}", flush=True)
                time.sleep(0.5)

    def start(self):
        """Start listening for wake word in background."""
        if self._running:
            return
        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop listening entirely."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._close_stream()

    def pause(self):
        """Pause wake word detection (e.g., while orchestrator is speaking/listening)."""
        self._paused = True

    def resume(self):
        """Resume wake word detection."""
        self._paused = False
        # Reset model state on resume to clear any stale predictions
        if self._model:
            self._model.reset()
