# Migration Guide: Google Speech → Whisper Voice

This guide helps you migrate from the existing Google Speech Recognition server to the new local Whisper-based server.

## Why Migrate?

### Privacy & Security
- **No Cloud Processing**: All speech recognition happens locally
- **No Data Transmission**: Your voice never leaves your machine
- **No Network Required**: Works completely offline
- **Full Control**: You own and control the entire pipeline

### Reliability
- **No API Limits**: No rate limits or quotas
- **No Service Outages**: No dependency on Google's infrastructure
- **Consistent Performance**: Predictable local processing
- **No Authentication**: No API keys or credentials needed

### Cost
- **Zero Ongoing Cost**: One-time model download, then free forever
- **No Cloud Bills**: Never pay for transcription
- **Resource Efficiency**: Models cached locally

## Key Differences

| Feature | Old (Google) | New (Whisper) |
|---------|-------------|---------------|
| Location | Cloud | Local |
| Internet | Required | Not required |
| Privacy | Data sent to Google | 100% local |
| Speed | Very fast | Moderate (CPU-dependent) |
| Models | Google's | tiny/base/small/medium |
| Setup | Simple | Install dependencies |
| First Use | Immediate | Model download required |

## Migration Steps

### Step 1: Install System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install portaudio19-dev python3-pyaudio ffmpeg

# Fedora
sudo dnf install portaudio-devel python3-pyaudio ffmpeg

# macOS
brew install portaudio ffmpeg
```

### Step 2: Install Python Dependencies

```bash
cd /home/connor/.claude/mcp-servers/whisper-voice
./setup.sh
```

Or manually:
```bash
pip install -r requirements.txt
```

### Step 3: Test the New Server

```bash
cd /home/connor/.claude/mcp-servers/whisper-voice
./test_server.sh
```

### Step 4: Update MCP Configuration

**Old configuration** (`~/.config/claude-code/mcp.json` or similar):
```json
{
  "mcpServers": {
    "voice": {
      "command": "python3",
      "args": ["/home/connor/voice-mcp-server/server.py"]
    }
  }
}
```

**New configuration**:
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

**Optional: Run Both During Transition**:
```json
{
  "mcpServers": {
    "voice-google": {
      "command": "python3",
      "args": ["/home/connor/voice-mcp-server/server.py"]
    },
    "whisper-voice": {
      "command": "python3",
      "args": ["/home/connor/.claude/mcp-servers/whisper-voice/server.py"]
    }
  }
}
```

### Step 5: Restart Claude Code

Restart Claude Code to load the new configuration.

### Step 6: Test Voice Input

```
You: "Listen for my voice input"
Claude: [Should now use Whisper server]
You: [Speak] "This is a test of the whisper voice server"
You: "stop claude"
```

### Step 7: Verify Model Download

On first use, the base.en model (~74MB) will download automatically.
Check the models directory:

```bash
ls -lh /home/connor/.claude/mcp-servers/whisper-voice/models/
```

### Step 8: Remove Old Server (Optional)

Once you've verified the new server works:

```bash
# Backup old server first
cp -r /home/connor/voice-mcp-server /home/connor/voice-mcp-server.backup

# Remove from MCP config
# (Edit your MCP config file to remove the old voice server)

# Optionally delete old server
# rm -rf /home/connor/voice-mcp-server
```

## API Compatibility

### Identical Functionality

Both servers provide the same tools with compatible parameters:

**listen tool** - Same parameters:
- `timeout` (integer, default: 10)
- `phrase_time_limit` (integer, default: 30)
- `stop_phrase` (string, default: "stop claude")

**NEW parameter** - Whisper adds:
- `model` (string, default: "base.en") - Choose Whisper model

**list_microphones tool** - Identical
- No parameters
- Same response format

### Response Format Changes

**Google Speech Response**:
```json
{
  "success": true,
  "text": "transcribed text",
  "message": "Transcribed: transcribed text"
}
```

**Whisper Response** (adds model field):
```json
{
  "success": true,
  "text": "transcribed text",
  "message": "Transcribed: transcribed text",
  "model": "base.en"
}
```

The extra `model` field is informational and doesn't break compatibility.

## Performance Tuning

### If Transcription is Too Slow

1. **Use faster model**:
   ```json
   {"model": "tiny.en"}
   ```

2. **Close other applications** to free CPU

3. **Monitor CPU usage**:
   ```bash
   htop
   ```

### If Accuracy is Insufficient

1. **Use larger model**:
   ```json
   {"model": "small.en"}
   ```
   or
   ```json
   {"model": "medium.en"}
   ```

2. **Improve audio quality**:
   - Use external microphone
   - Reduce background noise
   - Speak clearly

## Rollback Plan

If you need to revert to Google Speech:

### Quick Rollback

1. Edit MCP config, change back to old server path
2. Restart Claude Code
3. Done - old server still works

### Full Rollback

```bash
# Restore old config
cp ~/.config/claude-code/mcp.json.backup ~/.config/claude-code/mcp.json

# Restart Claude Code
# Old server should work immediately
```

## Troubleshooting Migration Issues

### Issue: "ModuleNotFoundError: No module named 'whisper'"

**Solution**:
```bash
pip install openai-whisper
```

### Issue: "PortAudio not found"

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install portaudio19-dev python3-pyaudio

# Then reinstall PyAudio
pip install --force-reinstall pyaudio
```

### Issue: "Permission denied" when accessing microphone

**Solution**:
```bash
# Add user to audio group (Linux)
sudo usermod -a -G audio $USER

# Log out and back in
```

### Issue: "Model download is too slow"

**Solution**: Download manually:
```bash
python3 -c "import whisper; whisper.load_model('base.en', download_root='/home/connor/.claude/mcp-servers/whisper-voice/models')"
```

### Issue: "Server not responding"

**Solution**: Check server logs:
```bash
python3 /home/connor/.claude/mcp-servers/whisper-voice/server.py 2>&1 | tee debug.log
# Send test request via stdin
```

## Feature Comparison

### Features Present in Both

- ✅ Voice transcription
- ✅ Stop phrase detection
- ✅ Microphone listing
- ✅ Timeout configuration
- ✅ Chunk-based listening
- ✅ Ambient noise adjustment
- ✅ MCP protocol compliance

### New Features in Whisper

- ✅ **Model selection** (tiny/base/small/medium)
- ✅ **Offline operation** (no internet required)
- ✅ **Local processing** (privacy-focused)
- ✅ **Model caching** (faster subsequent use)
- ✅ **No API dependencies** (self-contained)

### Features Only in Google

- ✅ **Cloud speed** (faster on slow CPUs)
- ✅ **Always latest** (Google updates models automatically)

## Best Practices After Migration

### 1. Start with Default Model

Use `base.en` (default) initially. It provides excellent balance.

### 2. Pre-warm the Server

On system startup, run a quick test to load the model:
```bash
# Add to startup script
python3 /home/connor/.claude/mcp-servers/whisper-voice/server.py << EOF &
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
EOF
```

### 3. Monitor Disk Space

Models take 500MB-1.5GB. Ensure sufficient space:
```bash
df -h /home/connor/.claude/mcp-servers/whisper-voice/models
```

### 4. Optimize for Your CPU

Test different models and find the sweet spot:
- **Fast CPU**: Try `small.en` or `medium.en`
- **Moderate CPU**: Stick with `base.en`
- **Slow CPU**: Use `tiny.en`

### 5. Configure Audio Properly

```bash
# Test microphone
arecord -d 5 test.wav && aplay test.wav

# List devices
python3 -c "import speech_recognition as sr; print('\n'.join(sr.Microphone.list_microphone_names()))"
```

## Long-term Maintenance

### Model Updates

Whisper models don't auto-update. To get newer versions:

1. Check OpenAI Whisper releases: https://github.com/openai/whisper
2. Update openai-whisper package:
   ```bash
   pip install --upgrade openai-whisper
   ```
3. Delete cached models to force re-download:
   ```bash
   rm -rf /home/connor/.claude/mcp-servers/whisper-voice/models/*
   ```

### Dependency Updates

Periodically update dependencies:
```bash
cd /home/connor/.claude/mcp-servers/whisper-voice
pip install --upgrade -r requirements.txt
```

### Server Updates

Watch for updates to the server code itself:
- Check for bug fixes
- Review new features
- Update configuration as needed

## Getting Help

### Check Logs

Server logs go to stderr:
```bash
python3 server.py 2>&1 | tee server.log
```

### Test Individual Components

**Test Whisper**:
```bash
python3 -c "
import whisper
model = whisper.load_model('base.en')
result = model.transcribe('test.wav')
print(result['text'])
"
```

**Test PyAudio**:
```bash
python3 -c "
import pyaudio
p = pyaudio.PyAudio()
print(f'Devices: {p.get_device_count()}')
"
```

**Test MCP Protocol**:
```bash
./test_server.sh
```

### Common Issues Database

| Symptom | Likely Cause | Solution |
|---------|-------------|----------|
| Slow transcription | Model too large | Use smaller model |
| Inaccurate text | Model too small | Use larger model |
| No speech detected | Mic permissions | Check audio group |
| Import errors | Missing deps | Run setup.sh |
| Download fails | Network/disk | Check connection & space |

## Success Checklist

- [ ] System dependencies installed
- [ ] Python dependencies installed
- [ ] Test script passes all tests
- [ ] MCP config updated
- [ ] Claude Code restarted
- [ ] Voice input tested successfully
- [ ] Model downloaded and cached
- [ ] Old server backed up
- [ ] Documentation reviewed

## Timeline Recommendation

**Week 1**: Install and test
- Install dependencies
- Run tests
- Try voice input in parallel with old server

**Week 2**: Use both servers
- Configure both in MCP
- Compare performance
- Adjust model selection

**Week 3**: Switch primary
- Make Whisper the default
- Keep old server as backup

**Week 4**: Decommission old server
- Remove from MCP config
- Archive old server code
- Full migration complete

## Support Resources

- **Whisper Documentation**: https://github.com/openai/whisper
- **MCP Protocol**: https://modelcontextprotocol.io
- **Server README**: `/home/connor/.claude/mcp-servers/whisper-voice/README.md`
- **Usage Examples**: `/home/connor/.claude/mcp-servers/whisper-voice/USAGE_EXAMPLES.md`

---

**Migration Questions?**

File issues or questions in your project repository.

**Ready to migrate?** Run `./setup.sh` to begin!
