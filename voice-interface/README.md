# Voice Command Interface for AI Tools

This project implements a voice command interface that allows you to interact with AI tools running in tmux panes using voice commands.

## Features

- Activate with Win+; hotkey combination
- Speak the tmux window number followed by your prompt
- End your command with "I am done" to send it to the specified window
- Works with any AI tools running in tmux panes

## Requirements

- Python 3.6+
- Linux, macOS, or Windows OS
- Microphone for voice input
- tmux installed and running

## Installation

1. Clone or download this repository
2. Navigate to the voice-interface directory
3. Run the setup script:

```bash
./setup.sh
```

This will install all required Python dependencies.

## Usage

1. Start your tmux session with your AI tools running in different windows
2. Run the voice interface:

```bash
python3 voice_interface.py
```

3. Press Ctrl+Alt+; to activate voice input
4. Speak the tmux window number followed by your prompt
5. End your command with "I am done"
6. Press Ctrl+C to exit the program

### Example

Say: "Window 2, help me debug this Python script, I am done"

This will send "help me debug this Python script" to tmux window 2.

## How It Works

1. The program listens for the Win+; hotkey combination
2. When activated, it starts listening for voice input
3. It processes the speech to extract the window number and command
4. It sends the command to the specified tmux window
5. The AI tool in that window receives and processes your command

## Troubleshooting

- If the hotkey doesn't work, check if your OS or another application is capturing the Win+; combination
- If speech recognition doesn't work, ensure your microphone is working and the required packages are installed
- If tmux commands fail, ensure tmux is running and the specified window exists

## Dependencies

- speechrecognition: For converting speech to text
- pynput: For detecting keyboard hotkeys
- pyautogui: For GUI automation (may be used in future enhancements)
- pyaudio: For audio processing