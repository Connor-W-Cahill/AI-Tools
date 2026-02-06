# Whisper Voice MCP Server - Quick Start

Get up and running with local voice transcription in 5 minutes.

## TL;DR

```bash
# 1. Install dependencies
cd /home/connor/.claude/mcp-servers/whisper-voice
./setup.sh

# 2. Test the server
./test_server.sh

# 3. Add to Claude Code config (~/.config/claude-code/mcp.json):
{
  "mcpServers": {
    "whisper-voice": {
      "command": "python3",
      "args": ["/home/connor/.claude/mcp-servers/whisper-voice/server.py"]
    }
  }
}

# 4. Restart Claude Code and start talking!
```

## Step-by-Step Setup

### 1. System Requirements

- **OS**: Linux (Ubuntu/Debian/Fedora), macOS, or Windows
- **Python**: 3.8 or later
- **CPU**: Any modern x86_64 (no GPU needed)
- **RAM**: 2 GB minimum, 4 GB recommended
- **Disk**: 1 GB free space
- **Microphone**: Any USB or built-in mic

### 2. Install System Dependencies

Choose your platform:

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio ffmpeg
```

**Fedora**:
```bash
sudo dnf install portaudio-devel python3-pyaudio ffmpeg
```

**macOS**:
```bash
brew install portaudio ffmpeg
```

### 3. Install Python Dependencies

```bash
cd /home/connor/.claude/mcp-servers/whisper-voice
./setup.sh
```

This will:
- Create the models directory
- Install all Python packages
- Make scripts executable
- Verify installation

**Manual installation** (if setup.sh fails):
```bash
pip install -r requirements.txt
# or with --user flag
pip install --user -r requirements.txt
```

### 4. Verify Installation

```bash
./test_server.sh
```

Expected output:
```
=========================================
Whisper Voice MCP Server Test
=========================================

[Test 1/4] Checking Python dependencies...
✓ All dependencies found

[Test 2/4] Listing available microphones...
✓ Found 3 microphone(s):
  0: HDA Intel PCH: ALC3246 Analog (hw:0,0)
  1: HDA Intel PCH: HDMI 0 (hw:0,3)
  2: default

[Test 3/4] Testing MCP protocol initialization...
✓ Server initialized: whisper-voice-input v1.0.0

[Test 4/4] Testing tools listing...
✓ Found 2 tool(s):
  - listen: Listen for voice input from the microphone...
  - list_microphones: List all available microphone devices...

=========================================
All Tests Passed! ✓
=========================================
```

### 5. Configure Claude Code

Add the server to your MCP configuration file.

**Location**: `~/.config/claude-code/mcp.json`

**Configuration**:
```json
{
  "mcpServers": {
    "whisper-voice": {
      "command": "python3",
      "args": ["/home/connor/.claude/mcp-servers/whisper-voice/server.py"]
    }
  }
}
```

**Tip**: If you have other MCP servers, add this to the existing `mcpServers` object.

### 6. Restart Claude Code

Close and reopen Claude Code to load the new server.

### 7. Test Voice Input

Try it out:

```
You: "I want to use voice input"
Claude: "I'll listen for your voice input now."
[Claude calls the listen tool]

[Microphone icon appears or you see "Listening..." in logs]

You: [Speak clearly] "Please create a hello world function in Python"
You: "stop claude"

Claude: "I'll create that function for you..."
```

## First Use Notes

### Model Download

On first use, Whisper will download the `base.en` model (~140 MB).

This happens automatically and only once. You'll see:
```
Loading Whisper model 'base.en'...
Model 'base.en' loaded successfully
```

**Download time**: 1-3 minutes on typical connection

**Storage location**: `/home/connor/.claude/mcp-servers/whisper-voice/models/`

### Performance Expectations

**First transcription**: 5-10 seconds (model loading)
**Subsequent transcriptions**: 1-3 seconds for 5-second audio

**If too slow**: Use a smaller model:
```
You: "Listen with the tiny model"
```

**If not accurate enough**: Use a larger model:
```
You: "Listen with the small model"
```

## Common First-Time Issues

### "No module named 'whisper'"

**Fix**:
```bash
pip install openai-whisper
```

### "PortAudio library not found"

**Fix**:
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev python3-pyaudio

# Fedora
sudo dnf install portaudio-devel

# macOS
brew install portaudio
```

### "Permission denied" accessing microphone

**Fix (Linux)**:
```bash
sudo usermod -a -G audio $USER
# Log out and back in
```

### "No speech detected"

**Fix**:
- Check microphone is connected and working
- Run `./test_server.sh` to see available microphones
- Speak louder or move closer to mic
- Test mic with: `arecord -d 5 test.wav && aplay test.wav`

## Usage Patterns

### Basic Usage

```
You: "Listen"
[Speak your input]
You: "stop claude"
```

### With Model Selection

```
You: "Listen with small model for better accuracy"
[Speak your input]
You: "stop claude"
```

### For Long Dictation

```
You: "Listen with 20 second timeout"
[Take your time to start speaking]
[Speak your input - can be several sentences]
You: "stop claude"
```

## What You Can Do

### Code Dictation
"Create a function called calculate sum that takes two numbers and returns their sum"

### Bug Reports
"When I click the submit button I get a null pointer exception on line 47"

### Feature Requests
"Add a dark mode toggle to the settings page with a moon icon"

### Documentation
"This function implements binary search on a sorted array and returns the index"

### Questions
"How do I configure environment variables in Docker compose"

## Tips for Best Results

1. **Speak clearly** - Enunciate technical terms
2. **Reduce noise** - Close windows, turn off fans
3. **Good microphone** - External mic better than built-in
4. **Proper distance** - 6-12 inches from mic
5. **Chunk long input** - Break into logical sections
6. **Say stop phrase** - Always end with "stop claude"

## Model Selection Guide

| Model | Speed | Accuracy | Use Case |
|-------|-------|----------|----------|
| tiny.en | Very Fast | Good | Quick commands |
| base.en | Fast | Better | General use (default) |
| small.en | Moderate | Great | Technical content |
| medium.en | Slow | Best | Complex/accented speech |

**Recommendation**: Start with `base.en` (default), adjust as needed.

## Next Steps

- Read [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) for detailed examples
- Check [README.md](README.md) for complete documentation
- See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Review [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) if migrating from Google Speech

## Getting Help

### Check Logs

```bash
# Run server manually to see logs
python3 /home/connor/.claude/mcp-servers/whisper-voice/server.py 2>&1 | tee debug.log
```

### Verify Components

```bash
# Test microphone
python3 -c "import speech_recognition as sr; print('\n'.join(sr.Microphone.list_microphone_names()))"

# Test Whisper
python3 -c "import whisper; print('Whisper installed:', whisper.__version__)"

# Test PyAudio
python3 -c "import pyaudio; p = pyaudio.PyAudio(); print('Devices:', p.get_device_count())"
```

### Common Commands

```bash
# Reinstall dependencies
pip install --force-reinstall -r requirements.txt

# Clear model cache
rm -rf models/*

# Check disk space
df -h /home/connor/.claude/mcp-servers/whisper-voice/

# Check permissions
ls -la /home/connor/.claude/mcp-servers/whisper-voice/
```

## Success Checklist

- [ ] System dependencies installed (portaudio, ffmpeg)
- [ ] Python dependencies installed (requirements.txt)
- [ ] Tests pass (./test_server.sh)
- [ ] MCP config updated with server path
- [ ] Claude Code restarted
- [ ] Voice input working in Claude Code
- [ ] Model downloaded and cached

## You're Ready!

Start dictating code, documentation, and more with complete privacy.

**Remember**: Everything runs locally. No cloud. No API keys. No data sharing.

Happy voice coding!

---

**Installation Issues?** Run `./test_server.sh` and check the output for specific errors.
