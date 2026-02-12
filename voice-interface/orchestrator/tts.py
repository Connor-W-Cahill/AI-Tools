"""
Text-to-speech engine using edge-tts (Microsoft Edge neural TTS).

Streams audio chunks directly to PulseAudio for low-latency playback.
"""

import asyncio
import os
import subprocess
import tempfile
import threading
from typing import Optional

import edge_tts

# Best natural-sounding voices (ranked)
VOICES = {
    "default": "en-GB-RyanNeural",      # Least robotic, British male
    "female": "en-US-EmmaMultilingualNeural",  # Natural US female
    "male_us": "en-US-GuyNeural",        # US male alternative
}

VOICE = VOICES["default"]


CACHE_DIR = os.path.expanduser("~/.cache/voice-orchestrator/tts")

# Phrases to pre-generate at startup for instant playback
PRECACHE_PHRASES = {
    "busy": "One moment.",
    "listening": "Listening.",
    "error": "Something went wrong.",
}


class TTS:
    def __init__(self, voice: str = VOICE):
        self.voice = voice
        self._speaking = False
        self._cancel = False
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._cache: dict[str, str] = {}  # key → filepath

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    def stop(self):
        """Interrupt current speech."""
        self._cancel = True
        with self._lock:
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._process.kill()
        self._speaking = False

    def speak(self, text: str):
        """Speak text synchronously (blocks until done or cancelled)."""
        if not text.strip():
            return
        self._cancel = False
        self._speaking = True
        try:
            asyncio.run(self._stream_speak(text))
        except Exception as e:
            print(f"[TTS] Error: {e}", flush=True)
        finally:
            self._speaking = False

    def speak_async(self, text: str) -> threading.Thread:
        """Speak text in background thread. Returns the thread."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t

    async def _stream_speak(self, text: str):
        """Stream audio from edge-tts directly to paplay for low latency."""
        communicate = edge_tts.Communicate(text, self.voice)

        # Write to temp file and play — edge-tts outputs MP3 chunks,
        # so we collect them and play with a single process for reliability
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        try:
            async for chunk in communicate.stream():
                if self._cancel:
                    break
                if chunk["type"] == "audio":
                    tmp.write(chunk["data"])
            tmp.close()

            if self._cancel:
                return

            # Play the audio file (ffplay is available, mpv may not be)
            with self._lock:
                self._process = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", tmp.name],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            self._process.wait()

        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass

    def precache(self):
        """Pre-generate common phrases as audio files for instant playback."""
        os.makedirs(CACHE_DIR, exist_ok=True)
        for key, phrase in PRECACHE_PHRASES.items():
            path = os.path.join(CACHE_DIR, f"{key}_{self.voice}.mp3")
            if os.path.exists(path):
                self._cache[key] = path
                continue
            try:
                asyncio.run(self._generate_to_file(phrase, path))
                self._cache[key] = path
                print(f"[TTS] Cached: {key}", flush=True)
            except Exception as e:
                print(f"[TTS] Cache failed for '{key}': {e}", flush=True)

    async def _generate_to_file(self, text: str, path: str):
        """Generate TTS audio to a persistent file."""
        communicate = edge_tts.Communicate(text, self.voice)
        with open(path, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])

    def play_cached(self, key: str):
        """Play a pre-cached phrase instantly. Non-blocking."""
        path = self._cache.get(key)
        if not path or not os.path.exists(path):
            return
        subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def play_cached_sync(self, key: str):
        """Play a pre-cached phrase and wait for it to finish."""
        path = self._cache.get(key)
        if not path or not os.path.exists(path):
            return
        proc = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        proc.wait()

    def set_voice(self, voice_key: str):
        """Switch voice by key (default, female, male_us) or full voice name."""
        if voice_key in VOICES:
            self.voice = VOICES[voice_key]
        else:
            self.voice = voice_key


# Module-level convenience
_tts = None

def get_tts() -> TTS:
    global _tts
    if _tts is None:
        _tts = TTS()
    return _tts

def speak(text: str):
    get_tts().speak(text)

def speak_async(text: str) -> threading.Thread:
    return get_tts().speak_async(text)

def stop():
    if _tts:
        _tts.stop()
