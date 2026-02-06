# Whisper Voice MCP Server

A privacy-focused Model Context Protocol (MCP) server that provides voice-to-text transcription using OpenAI's Whisper running **completely locally** on your machine. No cloud services, no external API calls.

## Features

- **100% Local Processing**: All speech recognition runs on your CPU using Whisper
- **No Cloud Dependencies**: Unlike Google Speech Recognition, everything stays on your machine
- **Model Selection**: Choose from tiny.en, base.en, small.en, or medium.en models
- **Model Caching**: Models are downloaded once and cached locally for fast subsequent use
- **Stop Phrase Detection**: Natural stopping with "stop claude" voice command
- **Continuous Listening**: Automatically captures multi-sentence speech
- **Silence Detection**: Stops when you stop talking
- **Microphone Management**: List and use available audio input devices

## Installation

### 1. Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev python3-pyaudio ffmpeg

# Fedora
sudo dnf install portaudio-devel python3-pyaudio ffmpeg

# macOS
brew install portaudio ffmpeg
```

### 2. Install Python Dependencies

```bash
cd /home/connor/.claude/mcp-servers/whisper-voice
pip install -r requirements.txt
```

### 3. Configure Claude Code

Add to your Claude Code MCP configuration (usually `~/.config/claude-code/mcp.json`):

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

## Usage

### Basic Voice Input

The server provides two MCP tools:

#### `listen` Tool

Captures voice input and transcribes it using Whisper:

```python
# Default usage (base.en model)
listen()

# With custom model
listen(model="small.en")

# With custom timeout and stop phrase
listen(
    model="base.en",
    timeout=15,
    phrase_time_limit=30,
    stop_phrase="stop claude"
)
```

**Parameters:**
- `model` (string, optional): Whisper model to use
  - `tiny.en`: Fastest, least accurate (~39M params)
  - `base.en`: **Default** - Good balance (~74M params)
  - `small.en`: Better accuracy (~244M params)
  - `medium.en`: Best accuracy, slower (~769M params)
- `timeout` (integer, default: 10): Seconds to wait for speech to start
- `phrase_time_limit` (integer, default: 30): Max seconds per listening chunk
- `stop_phrase` (string, default: "stop claude"): Voice command to stop

**Returns:**
```json
{
  "success": true,
  "text": "Your transcribed speech here",
  "message": "Transcribed: Your transcribed speech here",
  "model": "base.en"
}
```

#### `list_microphones` Tool

Lists available audio input devices:

```python
list_microphones()
```

**Returns:**
```json
{
  "success": true,
  "microphones": [
    "HDA Intel PCH: ALC3246 Analog (hw:0,0)",
    "HDA Intel PCH: HDMI 0 (hw:0,3)",
    "default"
  ],
  "count": 3
}
```

## Model Information

### Model Sizes and Performance

| Model | Size | Memory | Speed (CPU) | Accuracy |
|-------|------|--------|-------------|----------|
| tiny.en | ~39M | ~1 GB | ~32x faster | Good |
| base.en | ~74M | ~1 GB | ~16x faster | Better |
| small.en | ~244M | ~2 GB | ~6x faster | Great |
| medium.en | ~769M | ~5 GB | Baseline | Best |

**Recommendation**: Start with `base.en` (default). It provides excellent accuracy with reasonable CPU performance.

### Model Storage

Models are automatically downloaded on first use and cached at:
```
/home/connor/.claude/mcp-servers/whisper-voice/models/
```

## System Requirements

- **CPU**: Any modern x86_64 processor (no GPU required)
- **RAM**: 2-8 GB depending on model size
- **Storage**: 500 MB - 1.5 GB for model files
- **OS**: Linux (tested), macOS, Windows (with appropriate audio drivers)
- **Graphics**: Works on Intel UHD Graphics 630 (CPU-only processing)

## How It Works

1. **Audio Capture**: PyAudio + SpeechRecognition capture microphone input
2. **Chunked Listening**: Listens in 4-second chunks for responsive feedback
3. **Local Transcription**: Each chunk is processed by Whisper (completely offline)
4. **Stop Detection**: Monitors for stop phrase or silence
5. **Text Assembly**: Combines chunks into final transcription

## Privacy & Security

- **Zero Network Calls**: All processing happens locally
- **No Data Transmission**: Your voice never leaves your machine
- **No API Keys Required**: No cloud service credentials needed
- **Model Transparency**: Open-source Whisper models, inspectable code

## Troubleshooting

### Audio Device Issues

```bash
# Test microphone
python3 -c "import speech_recognition as sr; print(sr.Microphone.list_microphone_names())"

# Check audio permissions (Linux)
groups | grep audio
```

### Model Download Issues

```bash
# Manually download model
python3 -c "import whisper; whisper.load_model('base.en', download_root='/home/connor/.claude/mcp-servers/whisper-voice/models')"
```

### Performance Issues

- Try a smaller model: `tiny.en` or `base.en`
- Close other CPU-intensive applications
- Increase chunk timeout if transcription is slow

### Permission Denied on PyAudio

```bash
# Ubuntu/Debian
sudo usermod -a -G audio $USER
# Then log out and back in
```

## Comparison with Google Speech Recognition

| Feature | Whisper (This Server) | Google Speech Recognition |
|---------|----------------------|---------------------------|
| Privacy | 100% local | Cloud-based |
| Internet Required | No | Yes |
| API Keys | None | None (but cloud calls) |
| Accuracy | Excellent | Excellent |
| Speed | Moderate (CPU) | Fast (cloud) |
| Languages | 99+ languages | 100+ languages |
| Cost | Free | Free (with limits) |

## Technical Architecture

```
┌─────────────────┐
│   MCP Client    │
│  (Claude Code)  │
└────────┬────────┘
         │ JSON-RPC
         ▼
┌─────────────────┐
│  Whisper Voice  │
│   MCP Server    │
├─────────────────┤
│ • Model Cache   │
│ • Audio Handler │
│ • Transcription │
└────────┬────────┘
         │
    ┌────┴────┬──────────┐
    ▼         ▼          ▼
┌────────┐ ┌──────┐ ┌────────┐
│ Whisper│ │PyAudio│ │ Speech │
│  Model │ │       │ │  Recog │
└────────┘ └──────┘ └────────┘
```

## Development

### Running Tests

```bash
# Test microphone listing
python3 server.py <<EOF
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_microphones","arguments":{}}}
EOF
```

### Debugging

Enable verbose output:
```bash
python3 server.py 2>&1 | tee debug.log
```

## License

This server implementation: MIT License
OpenAI Whisper: MIT License
Dependencies: Various (see individual packages)

## Contributing

Improvements welcome! Areas for enhancement:
- Language selection beyond English
- Real-time streaming transcription
- GPU acceleration detection
- Noise reduction preprocessing
- Multiple microphone selection

## Credits

- **OpenAI Whisper**: https://github.com/openai/whisper
- **Model Context Protocol**: Anthropic
- **SpeechRecognition**: Anthony Zhang

## Support

For issues specific to:
- **This server**: File an issue at your project repo
- **Whisper models**: https://github.com/openai/whisper/issues
- **MCP protocol**: https://modelcontextprotocol.io
