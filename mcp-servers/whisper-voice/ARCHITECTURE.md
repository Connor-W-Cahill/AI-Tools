# Whisper Voice MCP Server - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Claude Code (Client)                     │
│                                                               │
│  User: "Listen for my voice input"                           │
│  Claude: [Calls mcp__whisper-voice__listen tool]             │
└────────────────────────┬──────────────────────────────────────┘
                         │ JSON-RPC 2.0 over stdio
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              Whisper Voice MCP Server                        │
│              (server.py)                                     │
│                                                              │
│  ┌──────────────────────────────────────────────────┐      │
│  │  MCP Protocol Handler                             │      │
│  │  - initialize                                     │      │
│  │  - tools/list                                     │      │
│  │  - tools/call                                     │      │
│  └───────────────┬──────────────────────────────────┘      │
│                  │                                           │
│  ┌───────────────▼──────────────────────────────────┐      │
│  │  WhisperVoiceMCPServer                            │      │
│  │                                                   │      │
│  │  ┌─────────────────────────────────────────┐    │      │
│  │  │  Model Cache                             │    │      │
│  │  │  - self.whisper_models = {}              │    │      │
│  │  │  - Lazy loading                          │    │      │
│  │  │  - Persistent across calls               │    │      │
│  │  └─────────────────────────────────────────┘    │      │
│  │                                                   │      │
│  │  ┌─────────────────────────────────────────┐    │      │
│  │  │  Audio Handler                           │    │      │
│  │  │  - speech_recognition.Recognizer         │    │      │
│  │  │  - speech_recognition.Microphone         │    │      │
│  │  │  - Ambient noise adjustment              │    │      │
│  │  │  - Chunk-based listening                 │    │      │
│  │  └─────────────────────────────────────────┘    │      │
│  │                                                   │      │
│  │  ┌─────────────────────────────────────────┐    │      │
│  │  │  Whisper Transcriber                     │    │      │
│  │  │  - Load model from cache                 │    │      │
│  │  │  - Convert AudioData → WAV               │    │      │
│  │  │  - Transcribe with Whisper               │    │      │
│  │  │  - Return text                           │    │      │
│  │  └─────────────────────────────────────────┘    │      │
│  │                                                   │      │
│  │  ┌─────────────────────────────────────────┐    │      │
│  │  │  Stop Phrase Detector                    │    │      │
│  │  │  - Regex matching                        │    │      │
│  │  │  - Case insensitive                      │    │      │
│  │  │  - Text cleaning                         │    │      │
│  │  └─────────────────────────────────────────┘    │      │
│  └───────────────────────────────────────────────────┘      │
└────────────┬────────────┬───────────────┬───────────────────┘
             │            │               │
        ┌────▼────┐  ┌───▼────┐   ┌──────▼─────┐
        │ PyAudio │  │Whisper │   │  Temp File │
        │         │  │ Model  │   │  System    │
        └────┬────┘  └───┬────┘   └──────┬─────┘
             │           │               │
        ┌────▼───────────▼───────────────▼─────┐
        │         Operating System              │
        │  - Audio drivers (ALSA/PulseAudio)    │
        │  - File system (/tmp/*.wav)           │
        │  - CPU scheduling                     │
        └───────────────────────────────────────┘
```

## Component Details

### 1. MCP Protocol Layer

**Purpose**: Handle JSON-RPC 2.0 communication with Claude Code

**Key Functions**:
- `read_request()`: Read JSON from stdin
- `send_response()`: Write JSON to stdout
- `handle_request()`: Route methods to handlers

**Supported Methods**:
- `initialize`: Handshake and capabilities exchange
- `notifications/initialized`: Acknowledge initialization
- `tools/list`: Return available tools
- `tools/call`: Execute a tool

**Protocol Compliance**:
- JSON-RPC 2.0 specification
- MCP 2024-11-05 protocol version
- Proper error codes and messages

### 2. Model Management

**Model Cache**:
```python
self.whisper_models = {}  # In-memory cache
self.models_dir = Path("models/")  # Disk cache
```

**Loading Strategy**:
1. Check if model in `self.whisper_models`
2. If not, load from disk cache via `whisper.load_model()`
3. Whisper checks `models/` directory first
4. If not found, downloads from OpenAI
5. Store in cache for future use

**Supported Models**:
| Model | Parameters | Disk Size | Memory |
|-------|-----------|-----------|---------|
| tiny.en | 39M | ~75 MB | ~1 GB |
| base.en | 74M | ~140 MB | ~1 GB |
| small.en | 244M | ~460 MB | ~2 GB |
| medium.en | 769M | ~1.5 GB | ~5 GB |

### 3. Audio Capture Pipeline

**Initialization**:
```python
self.recognizer = sr.Recognizer()
self.microphone = sr.Microphone()
self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
```

**Listening Loop**:
```python
for chunk in chunks:
    audio = recognizer.listen(
        source,
        timeout=timeout,
        phrase_time_limit=4  # 4-second chunks
    )
    text = transcribe_with_whisper(audio)
    if stop_phrase in text:
        break
```

**Audio Flow**:
1. Microphone → PyAudio → bytes
2. SpeechRecognition → AudioData object
3. AudioData → WAV bytes
4. WAV bytes → temp file
5. Temp file → Whisper model
6. Whisper → text

### 4. Transcription Engine

**Process**:
```python
def transcribe_audio_with_whisper(audio_data, model_name):
    # Get cached model
    model = get_whisper_model(model_name)

    # Convert to WAV
    wav_bytes = audio_data.get_wav_data()

    # Write temp file
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        tmp.write(wav_bytes)

        # Transcribe
        result = model.transcribe(
            tmp.name,
            language="en",
            fp16=False  # CPU mode
        )

    return result["text"]
```

**Whisper Parameters**:
- `language="en"`: English only (faster)
- `fp16=False`: Disable float16 (CPU compatibility)
- No other parameters (use defaults)

### 5. Stop Phrase Detection

**Implementation**:
```python
import re

if stop_phrase.lower() in chunk_text.lower():
    # Remove stop phrase from text
    cleaned = re.sub(
        re.escape(stop_phrase),
        '',
        chunk_text,
        flags=re.IGNORECASE
    ).strip()

    if cleaned:
        accumulated_text.append(cleaned)

    break  # Stop listening
```

**Features**:
- Case-insensitive matching
- Removes stop phrase from final text
- Preserves text before stop phrase
- Immediate stop on detection

### 6. Error Handling

**Levels**:
1. **JSON-RPC Errors**: Protocol violations
2. **Tool Errors**: Invalid parameters
3. **Runtime Errors**: Microphone, model, transcription failures

**Example**:
```python
try:
    audio = recognizer.listen(source, timeout=timeout)
except sr.WaitTimeoutError:
    return {
        "success": False,
        "message": "No speech detected within timeout period"
    }
except Exception as e:
    return {
        "success": False,
        "message": f"Error: {str(e)}"
    }
```

## Data Flow

### Successful Transcription

```
User speaks → Microphone
    ↓
PyAudio captures PCM audio
    ↓
SpeechRecognition packages as AudioData
    ↓
Convert to WAV format
    ↓
Write to temporary file
    ↓
Whisper model transcribes
    ↓
Text returned to server
    ↓
Check for stop phrase
    ↓
Accumulate text
    ↓
Return JSON response to Claude Code
    ↓
Claude Code receives transcription
```

### Model Loading (First Time)

```
Tool called with model="base.en"
    ↓
Check self.whisper_models cache → MISS
    ↓
Call whisper.load_model("base.en")
    ↓
Check disk cache (models/ dir) → MISS
    ↓
Download from OpenAI servers (~140 MB)
    ↓
Save to models/base.en.pt
    ↓
Load into memory
    ↓
Store in self.whisper_models["base.en"]
    ↓
Return model
    ↓
Ready for transcription
```

### Model Loading (Subsequent)

```
Tool called with model="base.en"
    ↓
Check self.whisper_models cache → HIT
    ↓
Return cached model
    ↓
Ready for transcription (instant)
```

## Performance Characteristics

### CPU Usage

**During Listening**:
- Low (< 5%) - mostly waiting for audio

**During Transcription**:
- High (50-100%) - Whisper inference
- Duration depends on:
  - Model size (tiny < base < small < medium)
  - Audio length
  - CPU speed

### Memory Usage

**Base Memory**:
- Python interpreter: ~50 MB
- SpeechRecognition: ~20 MB
- Server code: ~10 MB

**Per Model** (resident in RAM):
- tiny.en: ~1 GB
- base.en: ~1 GB
- small.en: ~2 GB
- medium.en: ~5 GB

**Note**: Models persist in memory for server lifetime

### Disk Usage

**Installation**:
- Dependencies: ~1 GB
- PyTorch: ~700 MB
- Whisper package: ~50 MB

**Runtime**:
- Temp files: < 10 MB (deleted immediately)
- Model cache: 75 MB - 1.5 GB per model

### Network Usage

**Installation**: ~1 GB (one-time)
**Runtime**: 0 bytes (completely offline)

## Security Considerations

### Threat Model

**Local Privilege**:
- Server runs with user permissions
- Can access user's microphone
- Can write to models/ directory
- Can create temp files

**No Network Access**:
- No outbound connections after setup
- No data exfiltration risk
- No external API dependencies

### Security Features

**Input Validation**:
```python
valid_models = ["tiny.en", "base.en", "small.en", "medium.en"]
if model not in valid_models:
    return error
```

**Resource Limits**:
```python
max_chunks = 30  # Max ~2 minutes
chunk_duration = 4  # 4-second chunks
```

**File Safety**:
```python
# Temp files with automatic cleanup
with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    # ...
    os.unlink(tmp.name)  # Explicit cleanup
```

**Error Boundaries**:
- All exceptions caught and logged
- No uncaught exceptions crash server
- Graceful degradation

## Scalability

### Single-User Design

**Assumptions**:
- One user at a time
- One voice input at a time
- Sequential processing

**Limitations**:
- No concurrent transcription
- No multi-user support
- No request queuing

**Rationale**:
- MCP servers are personal tools
- Voice input is inherently sequential
- Simplicity over complexity

### Resource Constraints

**CPU Bound**:
- Transcription is CPU-intensive
- No GPU acceleration (by design)
- Performance scales with CPU speed

**Memory Bound**:
- Models must fit in RAM
- No model swapping
- Cache persists for server lifetime

## Extensibility

### Adding New Models

```python
# Simply add to valid_models list
valid_models = ["tiny.en", "base.en", "small.en", "medium.en", "large"]

# Whisper will auto-download if available
```

### Adding Languages

```python
# Modify transcribe call
result = model.transcribe(
    tmp_path,
    language=language,  # Pass as parameter
    fp16=False
)
```

### Adding GPU Support

```python
# Detect GPU
import torch
has_gpu = torch.cuda.is_available()

# Use FP16 if GPU available
result = model.transcribe(
    tmp_path,
    language="en",
    fp16=has_gpu
)
```

## Debugging

### Log Levels

**stderr output**:
- Model loading messages
- "Listening..." prompts
- "heard: {text}" chunks
- Stop phrase detection
- Error messages

**stdout**:
- JSON-RPC responses only
- Never polluted by logs

### Debug Mode

Enable verbose logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Test Harness

```bash
# Send requests directly
./test_server.sh

# Or manually
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python3 server.py
```

## Future Improvements

### Potential Enhancements

1. **Streaming Transcription**: Real-time word-by-word output
2. **GPU Auto-Detection**: Use GPU if available
3. **Model Auto-Selection**: Choose model based on CPU speed
4. **Noise Reduction**: Preprocessing with librosa
5. **Speaker Diarization**: Multiple speaker detection
6. **Punctuation Restoration**: Better formatting
7. **Custom Vocabulary**: Domain-specific terms
8. **Audio Compression**: Smaller temp files

### Non-Goals

- Multi-user support (out of scope)
- Cloud integration (defeats privacy goal)
- Real-time streaming (complexity vs. benefit)
- Video/screen recording (different domain)

## Dependencies Graph

```
server.py
├── Python 3.8+
├── speech_recognition
│   ├── PyAudio
│   │   └── portaudio (system)
│   └── typing
├── openai-whisper
│   ├── torch
│   │   └── numpy
│   ├── torchaudio
│   ├── ffmpeg-python (optional)
│   └── numba (optional)
└── Standard library
    ├── json
    ├── sys
    ├── os
    ├── re
    ├── tempfile
    └── pathlib
```

## Deployment Architecture

### Single Machine

```
/home/connor/.claude/mcp-servers/whisper-voice/
├── server.py          # Main server
├── requirements.txt   # Python deps
├── models/            # Model cache
│   ├── base.en.pt
│   ├── tiny.en.pt
│   └── small.en.pt
├── setup.sh           # Installation
├── test_server.sh     # Testing
└── *.md               # Documentation
```

### Process Model

```
Claude Code (PID 1234)
    │
    └─ spawns ─> python3 server.py (PID 5678)
                     │
                     ├─ stdin  ← JSON-RPC requests
                     ├─ stdout → JSON-RPC responses
                     └─ stderr → Logs
```

### Lifecycle

1. **Startup**: Claude Code spawns server
2. **Initialization**: MCP handshake
3. **Ready**: Server waits for tool calls
4. **Tool Call**: Process request, return response
5. **Idle**: Wait for next call
6. **Shutdown**: Claude Code terminates server

---

**Architecture Version**: 1.0.0
**Last Updated**: 2026-01-21
**Maintained By**: Connor (AI-Tools project)
