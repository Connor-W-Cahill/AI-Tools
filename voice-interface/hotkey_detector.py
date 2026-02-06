#!/usr/bin/env python3
"""
Hotkey detector for voice interface
Uses the keyboard library to detect Ctrl+Alt+; and trigger the voice interface
"""

import keyboard
import time
import os
import subprocess

def trigger_voice_interface():
    """Create a signal file to trigger the voice interface"""
    signal_file = "/tmp/voice_interface_signal"
    with open(signal_file, "w") as f:
        f.write("activate")

    # Clean up after a short delay
    time.sleep(0.5)
    if os.path.exists(signal_file):
        os.remove(signal_file)

def main():
    print("Hotkey detector started. Press Ctrl+Alt+; to activate voice interface...")

    # Register the hotkey combination - using Ctrl+Alt+; to avoid conflicts
    keyboard.add_hotkey('ctrl+alt+;', trigger_voice_interface)

    print("Hotkey registered: Ctrl+Alt+; (to avoid conflicts with terminal shortcuts)")
    print("Press Ctrl+Alt+; to activate the voice interface")
    print("Press ESC to exit")

    # Wait indefinitely for hotkey
    keyboard.wait('esc')

if __name__ == "__main__":
    main()