#!/usr/bin/env python3
"""
Speaker verification using resemblyzer voice embeddings.

Compares captured audio against an enrolled speaker profile to reject
commands from background audio, music, or other people.
"""

from __future__ import annotations

import os
import struct

import numpy as np
import speech_recognition as sr
from resemblyzer import VoiceEncoder, preprocess_wav

PROFILE_DIR = os.path.expanduser("~/.cache/voice-orchestrator")
PROFILE_PATH = os.path.join(PROFILE_DIR, "speaker_profile.npy")
DEFAULT_THRESHOLD = 0.65


class SpeakerVerifier:
    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        self.threshold = threshold
        self._encoder = None
        self._profile: np.ndarray | None = None

        if self.is_enrolled():
            self._profile = np.load(PROFILE_PATH)
            print(f"[SpeakerVerify] Loaded speaker profile ({self._profile.shape})", flush=True)
        else:
            print("[SpeakerVerify] No speaker profile found — verification disabled", flush=True)

    def _load_encoder(self):
        if self._encoder is None:
            print("[SpeakerVerify] Loading voice encoder...", flush=True)
            self._encoder = VoiceEncoder()
            print("[SpeakerVerify] Voice encoder ready.", flush=True)

    def is_enrolled(self) -> bool:
        return os.path.isfile(PROFILE_PATH)

    def enroll(self, audio_samples: list[sr.AudioData]):
        """Extract embeddings from multiple audio samples, average them, and save."""
        self._load_encoder()
        embeddings = []
        for i, audio in enumerate(audio_samples):
            wav = self._audio_to_wav_array(audio)
            wav = preprocess_wav(wav)
            if len(wav) < 1600:  # < 0.1s at 16kHz
                print(f"[SpeakerVerify] Sample {i+1} too short, skipping", flush=True)
                continue
            emb = self._encoder.embed_utterance(wav)
            embeddings.append(emb)
            print(f"[SpeakerVerify] Enrolled sample {i+1}/{len(audio_samples)}", flush=True)

        if not embeddings:
            raise ValueError("No valid audio samples for enrollment")

        self._profile = np.mean(embeddings, axis=0)
        os.makedirs(PROFILE_DIR, exist_ok=True)
        np.save(PROFILE_PATH, self._profile)
        print(f"[SpeakerVerify] Profile saved to {PROFILE_PATH}", flush=True)

    def verify(self, audio: sr.AudioData) -> tuple[bool, float]:
        """Compare audio against enrolled profile. Returns (is_match, similarity)."""
        if self._profile is None:
            return True, 1.0  # no profile = pass through

        self._load_encoder()
        wav = self._audio_to_wav_array(audio)
        wav = preprocess_wav(wav)
        if len(wav) < 1600:
            return False, 0.0

        emb = self._encoder.embed_utterance(wav)
        similarity = float(np.dot(emb, self._profile) / (
            np.linalg.norm(emb) * np.linalg.norm(self._profile)
        ))
        is_match = similarity >= self.threshold
        return is_match, similarity

    @staticmethod
    def _audio_to_wav_array(audio: sr.AudioData) -> np.ndarray:
        """Convert speech_recognition AudioData to float32 numpy array at 16kHz."""
        raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
        samples = struct.unpack(f"<{len(raw)//2}h", raw)
        return np.array(samples, dtype=np.float32) / 32768.0
