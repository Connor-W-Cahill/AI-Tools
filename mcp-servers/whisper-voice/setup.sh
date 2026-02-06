#!/bin/bash
# Setup script for Whisper Voice MCP Server

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "========================================="
echo "Whisper Voice MCP Server Setup"
echo "========================================="
echo ""

# Check Python version
echo "[1/5] Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "Error: Python 3 not found. Please install Python 3.8 or later."
    exit 1
fi

# Check for system dependencies
echo ""
echo "[2/5] Checking system dependencies..."

if command -v apt-get &> /dev/null; then
    echo "Detected apt-based system (Ubuntu/Debian)"
    echo "Required packages: portaudio19-dev python3-pyaudio ffmpeg"
    echo "Run: sudo apt-get install portaudio19-dev python3-pyaudio ffmpeg"
elif command -v dnf &> /dev/null; then
    echo "Detected dnf-based system (Fedora)"
    echo "Required packages: portaudio-devel python3-pyaudio ffmpeg"
    echo "Run: sudo dnf install portaudio-devel python3-pyaudio ffmpeg"
elif command -v brew &> /dev/null; then
    echo "Detected macOS with Homebrew"
    echo "Required packages: portaudio ffmpeg"
    echo "Run: brew install portaudio ffmpeg"
else
    echo "Unknown package manager. Please install PortAudio and FFmpeg manually."
fi

# Create models directory
echo ""
echo "[3/5] Creating models directory..."
mkdir -p models
echo "Models will be cached in: $SCRIPT_DIR/models"

# Install Python dependencies
echo ""
echo "[4/5] Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install Python dependencies"
        echo "Try: pip install --user -r requirements.txt"
        exit 1
    fi
else
    echo "Error: requirements.txt not found"
    exit 1
fi

# Make server executable
echo ""
echo "[5/5] Making server executable..."
chmod +x server.py

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Test the server: ./test_server.sh"
echo "2. Add to Claude Code MCP config:"
echo ""
echo '   {
     "mcpServers": {
       "whisper-voice": {
         "command": "python3",
         "args": ["'$SCRIPT_DIR'/server.py"]
       }
     }
   }'
echo ""
echo "Models will be auto-downloaded on first use (this may take a few minutes)."
echo "Default model: base.en (~74MB)"
echo ""
