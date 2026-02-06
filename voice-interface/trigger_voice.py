#!/usr/bin/env python3
"""
Trigger script for voice interface
This script is called by xbindkeys when the hotkey is pressed
"""

import subprocess
import os

def trigger_voice_interface():
    """
    Signal the main voice interface to start listening
    """
    # Create a temporary file to signal the main app
    signal_file = "/tmp/voice_interface_signal"
    with open(signal_file, "w") as f:
        f.write("activate")
    
    # Wait a bit and then remove the signal file
    import time
    time.sleep(0.5)
    if os.path.exists(signal_file):
        os.remove(signal_file)

if __name__ == "__main__":
    trigger_voice_interface()