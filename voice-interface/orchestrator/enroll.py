#!/usr/bin/env python3
"""
Speaker enrollment script for Jarvis voice verification.

Records 3 voice samples, extracts embeddings, and saves the speaker profile.
Run once: python3 enroll.py
"""

from __future__ import annotations

import ctypes
import ctypes.util
import sys
import time

import speech_recognition as sr

# Suppress ALSA warnings
try:
    asound = ctypes.cdll.LoadLibrary(ctypes.util.find_library("asound") or "libasound.so.2")
    c_type = ctypes.CFUNCTYPE(None, ctypes.c_char_p, ctypes.c_int,
                              ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p)
    _handler = c_type(lambda *a: None)
    asound.snd_lib_error_set_handler(_handler)
except Exception:
    pass

from speaker_verify import SpeakerVerifier

PROMPTS = [
    "Please say: 'Hey Jarvis, what time is it?'",
    "Please say: 'Check the status of window one.'",
    "Please say: 'Tell me what's on my screen right now.'",
]

LISTEN_TIMEOUT = 10
PHRASE_LIMIT = 10


def main():
    print("=== Jarvis Speaker Enrollment ===\n")
    print("This will record 3 voice samples to create your speaker profile.")
    print("Speak naturally, as you would when talking to Jarvis.\n")

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    # Calibrate
    print("Calibrating microphone (2s silence)...", flush=True)
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=2)
    print("Calibration done.\n")

    samples: list[sr.AudioData] = []

    for i, prompt in enumerate(PROMPTS):
        print(f"Sample {i+1}/{len(PROMPTS)}: {prompt}")
        input("Press Enter when ready, then speak... ")
        print("  Listening...", flush=True)

        try:
            with mic as source:
                audio = recognizer.listen(
                    source, timeout=LISTEN_TIMEOUT, phrase_time_limit=PHRASE_LIMIT
                )
            samples.append(audio)
            print(f"  Got it! ({len(audio.get_raw_data()) / 32000:.1f}s of audio)\n")
        except sr.WaitTimeoutError:
            print("  No speech detected. Try again.")
            i -= 1
            continue

    print("Enrolling speaker profile...", flush=True)
    verifier = SpeakerVerifier()
    verifier.enroll(samples)

    # Quick self-test
    print("\nSelf-test: verifying last sample against profile...")
    is_match, score = verifier.verify(samples[-1])
    print(f"  Match: {is_match}, Similarity: {score:.3f}")

    if is_match:
        print("\nEnrollment successful! Restart the orchestrator service:")
        print("  systemctl --user restart voice-orchestrator")
    else:
        print("\nWarning: self-test failed. You may want to re-enroll.")
        print("Try speaking closer to the microphone.")
        sys.exit(1)


if __name__ == "__main__":
    main()
