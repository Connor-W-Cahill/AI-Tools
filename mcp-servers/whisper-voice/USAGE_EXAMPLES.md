# Whisper Voice MCP Server - Usage Examples

## Quick Start

Once configured in Claude Code, you can use voice input naturally:

### Example 1: Basic Voice Input

```
You: "I want to give you voice input"
Claude: [Calls listen tool]
You: [Speaking] "Please create a function that calculates the fibonacci sequence"
You: "stop claude"
Claude: "I'll create that fibonacci function for you..."
```

### Example 2: Using Different Models

```
You: "Listen with the small model for better accuracy"
Claude: [Calls listen with model="small.en"]
You: [Speaking technical content]
```

### Example 3: Longer Timeout for Thinking

```
You: "Listen for my input, I need time to think"
Claude: [Calls listen with timeout=20]
You: [Takes time to formulate thoughts]
You: [Starts speaking]
```

## Tool Usage Patterns

### listen Tool

**Simple dictation:**
```json
{
  "name": "listen",
  "arguments": {}
}
```

**Fast transcription (tiny model):**
```json
{
  "name": "listen",
  "arguments": {
    "model": "tiny.en"
  }
}
```

**High accuracy (small model):**
```json
{
  "name": "listen",
  "arguments": {
    "model": "small.en"
  }
}
```

**Maximum accuracy (medium model - slow):**
```json
{
  "name": "listen",
  "arguments": {
    "model": "medium.en"
  }
}
```

**Custom stop phrase:**
```json
{
  "name": "listen",
  "arguments": {
    "stop_phrase": "that's all"
  }
}
```

**Long-form dictation:**
```json
{
  "name": "listen",
  "arguments": {
    "timeout": 15,
    "phrase_time_limit": 60
  }
}
```

### list_microphones Tool

**Check available devices:**
```json
{
  "name": "list_microphones",
  "arguments": {}
}
```

## Response Examples

### Successful Transcription

```json
{
  "success": true,
  "text": "Please create a function that calculates the fibonacci sequence",
  "message": "Transcribed: Please create a function that calculates the fibonacci sequence",
  "model": "base.en"
}
```

### No Speech Detected

```json
{
  "success": false,
  "text": "",
  "message": "No speech detected within timeout period"
}
```

### Invalid Model

```json
{
  "success": false,
  "text": "",
  "message": "Invalid model 'large.en'. Must be one of: tiny.en, base.en, small.en, medium.en"
}
```

## Model Selection Guide

### When to Use Each Model

**tiny.en** - Use when:
- You need very fast responses
- Voice commands are short and simple
- CPU resources are limited
- You don't mind occasional errors

**base.en** (Default) - Use when:
- You want balanced performance
- General purpose dictation
- Reasonable accuracy is sufficient
- Most common use case

**small.en** - Use when:
- You need better accuracy
- Technical terminology is involved
- You can wait a bit longer
- CPU can handle it

**medium.en** - Use when:
- Maximum accuracy is required
- Complex technical content
- Accents or difficult audio
- You have time and CPU resources

## Real-World Scenarios

### Scenario 1: Code Dictation

```
You: "Listen for code description"
[Speaking]: "Create a Python class called DatabaseConnection with methods
            connect, disconnect, and execute query. The connect method
            should take host, port, username and password as parameters."
You: "stop claude"
```

**Best model**: `small.en` or `medium.en` (technical terms)

### Scenario 2: Quick Commands

```
You: "Listen for command"
[Speaking]: "Run the tests"
```

**Best model**: `tiny.en` or `base.en` (simple, fast)

### Scenario 3: Documentation Dictation

```
You: "Listen for documentation with high accuracy"
[Speaking]: "This function implements the Dijkstra shortest path algorithm.
            It takes a weighted graph represented as an adjacency matrix
            and returns the shortest path between source and destination nodes."
You: "stop claude"
```

**Best model**: `small.en` or `medium.en` (technical, detailed)

### Scenario 4: Bug Description

```
You: "Listen to bug report"
[Speaking]: "When I click the submit button on the user registration form,
            I get a null pointer exception. The stack trace shows it's
            happening in the validateEmail method on line 47."
You: "stop claude"
```

**Best model**: `base.en` or `small.en` (good balance)

## Tips for Best Results

### Audio Quality

1. **Speak clearly** - Enunciate technical terms
2. **Reduce background noise** - Close windows, turn off fans
3. **Use a good microphone** - External mic better than built-in
4. **Maintain distance** - 6-12 inches from microphone
5. **Avoid echo** - Soft furnishings help

### Dictation Technique

1. **Pause between thoughts** - Server listens in chunks
2. **Spell technical terms** - "camelCase, that's C-A-M-E-L-C-A-S-E"
3. **Use punctuation verbally** - "period", "comma", "new line"
4. **Chunk long input** - Break into logical sections
5. **Say stop phrase clearly** - Don't rush "stop claude"

### Performance Optimization

1. **Pre-load models** - First use downloads and caches
2. **Choose right model** - Don't use medium.en for simple commands
3. **Monitor CPU** - Large models can max out CPU
4. **Close other apps** - Free up system resources
5. **Adjust timeouts** - Increase if you need thinking time

## Troubleshooting Common Issues

### "No speech detected"

**Problem**: Microphone not picking up audio
**Solutions**:
- Check microphone permissions
- Run `list_microphones` to verify device
- Increase timeout parameter
- Speak louder or move closer
- Test with: `arecord -d 5 test.wav` (Linux)

### "Transcription is slow"

**Problem**: Model too large for CPU
**Solutions**:
- Use smaller model (base.en or tiny.en)
- Close other CPU-intensive apps
- Check system load with `top` or `htop`
- Consider upgrading hardware

### "Inaccurate transcription"

**Problem**: Wrong words or gibberish
**Solutions**:
- Use larger model (small.en or medium.en)
- Improve audio quality
- Speak more clearly
- Reduce background noise
- Check microphone positioning

### "Model download fails"

**Problem**: Network or disk issues
**Solutions**:
- Check internet connection
- Verify disk space (need 1-2 GB)
- Check write permissions on models/ directory
- Try manual download: `python3 -c "import whisper; whisper.load_model('base.en')"`

### "Import errors"

**Problem**: Missing Python dependencies
**Solutions**:
- Run `./setup.sh` again
- Manually install: `pip install -r requirements.txt`
- Check Python version: `python3 --version` (need 3.8+)
- Try with --user flag: `pip install --user -r requirements.txt`

## Performance Benchmarks

Approximate transcription times on Intel i5-8250U CPU:

| Model | 5s audio | 30s audio | Memory |
|-------|----------|-----------|--------|
| tiny.en | 0.5s | 3s | ~1 GB |
| base.en | 1s | 6s | ~1 GB |
| small.en | 3s | 18s | ~2 GB |
| medium.en | 10s | 60s | ~5 GB |

*Your mileage may vary based on CPU speed and system load*

## Integration Examples

### With Claude Code

```
User: "I want to dictate some code changes"
Claude: "I'll listen for your input."
[Calls listen tool with default settings]

[User speaks]: "In the file utils.py, change the timeout variable from
                30 to 60 seconds, and add a comment explaining that this
                is for slow network connections."

Claude: "I'll make those changes to utils.py..."
[Edits file as described]
```

### With Long Descriptions

```
User: "Listen with the small model for a detailed explanation"
Claude: [Calls listen with model="small.en"]

[User speaks for 1-2 minutes explaining complex algorithm]

User: "stop claude"
Claude: [Receives full transcription and responds]
```

## Advanced Usage

### Environment Variables

```bash
# Set custom model cache location
export WHISPER_CACHE_DIR=/path/to/cache

# Run server
python3 server.py
```

### Programmatic Usage (Python)

```python
import json
import subprocess

# Start server
server = subprocess.Popen(
    ['python3', 'server.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

# Send initialize request
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "listen",
        "arguments": {
            "model": "base.en",
            "timeout": 10
        }
    }
}

server.stdin.write(json.dumps(request) + '\n')
server.stdin.flush()

# Read response
response = json.loads(server.stdout.readline())
print(response)
```

## Comparison with Google Speech

### Privacy

| Feature | Whisper | Google |
|---------|---------|--------|
| Data location | Local only | Cloud processing |
| Internet required | No | Yes |
| Data retention | None | Per Google policy |
| Third-party access | None | Potential |

### Performance

| Feature | Whisper | Google |
|---------|---------|--------|
| Speed | Moderate (CPU) | Fast (cloud) |
| Accuracy | Excellent | Excellent |
| Offline | Yes | No |
| Cost | Free | Free (limits) |

### Use Cases

**Use Whisper when:**
- Privacy is critical
- Working with sensitive data
- No internet connection
- Long-term sustainability matters
- You control the infrastructure

**Use Google when:**
- Speed is critical
- Internet always available
- Don't mind cloud processing
- Need absolute latest model updates
