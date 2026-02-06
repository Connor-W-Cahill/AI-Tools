#!/bin/bash

# Setup script for Voice Command Interface

echo "Setting up Voice Command Interface for AIs..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Check if the installation was successful
if [ $? -eq 0 ]; then
    echo "Dependencies installed successfully!"
    echo ""
    echo "To run the voice interface:"
    echo "  python3 voice_interface.py"
    echo ""
    echo "Instructions:"
    echo "- Press Win+; to activate voice input"
    echo "- Speak the tmux window number followed by your prompt"
    echo "- End your command with 'I am done'"
    echo "- Press ESC to exit the program"
    echo ""
    echo "Example: Say 'Window 2, help me debug this Python script, I am done'"
    echo "This will send 'help me debug this Python script' to tmux window 2"
else
    echo "Failed to install dependencies. Please check your Python and pip installation."
    exit 1
fi