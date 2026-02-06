#!/usr/bin/env python3
"""
Voice Command Interface for AI Tools
Activates with Win+; and allows voice input to tmux panes
"""

import os
import sys
import subprocess
import threading
import time
import signal
import json
from datetime import datetime

import speech_recognition as sr

class VoiceInterface:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.listener_active = False

        # Configure the recognizer
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)

    def start_voice_input(self):
        """Start listening for voice input"""
        if self.listener_active:
            print("Voice interface already active.")
            return

        self.listener_active = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Voice interface activated. Listening...")

        # Create a thread to handle the voice recognition
        voice_thread = threading.Thread(target=self.listen_for_command)
        voice_thread.daemon = True
        voice_thread.start()

    def listen_for_command(self):
        """Listen for the voice command"""
        try:
            with self.microphone as source:
                print("Listening for window number and prompt...")
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)

            print("Processing speech...")
            text = self.recognizer.recognize_google(audio)
            print(f"Heard: {text}")

            # Parse the command
            self.process_command(text.lower())

        except sr.WaitTimeoutError:
            print("Timeout: No speech detected")
        except sr.UnknownValueError:
            print("Could not understand audio")
        except sr.RequestError as e:
            print(f"Error with speech recognition service: {e}")
        finally:
            self.listener_active = False

    def process_command(self, text):
        """Parse the command to extract window number and prompt"""
        # Look for "I am done" to identify the end of the command
        if "i am done" in text:
            # Extract everything before "i am done"
            command_part = text.split("i am done")[0].strip()

            # Try to extract the window number (first number in the command)
            import re
            numbers = re.findall(r'\d+', command_part)

            if numbers:
                window_num = int(numbers[0])

                # Remove the window number from the command
                command_without_window = re.sub(r'^\s*\d+\s*', '', command_part).strip()

                print(f"Target window: {window_num}")
                print(f"Command: {command_without_window}")

                # Send the command to the specified tmux window
                self.send_to_tmux(window_num, command_without_window)
            else:
                print("No window number found in command")
                print("Please speak the window number followed by your prompt, then say 'I am done'")
        else:
            print("Command must end with 'I am done'")

    def send_to_tmux(self, window_num, command):
        """Send the command to the specified tmux window"""
        try:
            # Check if tmux is running
            result = subprocess.run(['tmux', 'list-sessions'],
                                  capture_output=True, text=True, check=False)

            if result.returncode != 0:
                print("Error: tmux is not running")
                return

            # Focus on the specified window
            focus_cmd = ['tmux', 'select-window', '-t', str(window_num)]
            result = subprocess.run(focus_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"Error: tmux window {window_num} does not exist")
                return

            # Send the command to the active pane
            send_cmd = ['tmux', 'send-keys', '-t', str(window_num), command, 'Enter']
            result = subprocess.run(send_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"Command sent to tmux window {window_num}")
            else:
                print(f"Error sending command to tmux window {window_num}: {result.stderr}")

        except Exception as e:
            print(f"Error communicating with tmux: {e}")

    def monitor_signal_file(self):
        """Monitor for signal file to activate voice input"""
        signal_file = "/tmp/voice_interface_signal"
        while True:
            if os.path.exists(signal_file):
                # Remove the signal file and activate voice input
                os.remove(signal_file)
                self.start_voice_input()
            time.sleep(0.1)  # Check every 100ms

    def run(self):
        """Run the voice interface"""
        print("Voice Interface for AI Tools started.")
        print("Waiting for activation signal (Ctrl+Alt+; key combination).")
        print("Speak the window number followed by your prompt, then say 'I am done'.")
        print("Press Ctrl+C to exit.")

        # Start monitoring for the signal file in a separate thread
        signal_thread = threading.Thread(target=self.monitor_signal_file)
        signal_thread.daemon = True
        signal_thread.start()

        # Keep the main thread alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down voice interface...")
            sys.exit(0)

def main():
    # Check if required packages are installed
    try:
        import speech_recognition
    except ImportError as e:
        print(f"Missing required package: {e}")
        print("Please install required packages with: pip install speechrecognition")
        sys.exit(1)

    # Create and run the voice interface
    interface = VoiceInterface()
    interface.run()

if __name__ == "__main__":
    main()