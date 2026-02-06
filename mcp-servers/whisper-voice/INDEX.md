# Whisper Voice MCP Server - Documentation Index

Welcome! This index helps you find the right documentation for your needs.

## I Want To...

### Get Started Quickly
→ **[QUICKSTART.md](QUICKSTART.md)** - 5-minute setup guide with step-by-step instructions

### Understand What This Does
→ **[README.md](README.md)** - Complete feature overview and documentation
→ **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - High-level project overview

### Migrate from Google Speech
→ **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Detailed migration steps and comparison

### Learn How to Use It
→ **[USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)** - Real-world examples and tips

### Understand How It Works
→ **[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical deep-dive and design docs

## By Role

### I'm a User
**Start Here**: [QUICKSTART.md](QUICKSTART.md)
**Then Read**: [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)
**Reference**: [README.md](README.md)

### I'm Migrating from Google Speech
**Start Here**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
**Then Read**: [QUICKSTART.md](QUICKSTART.md)
**Reference**: [README.md](README.md)

### I'm a Developer
**Start Here**: [ARCHITECTURE.md](ARCHITECTURE.md)
**Then Read**: [README.md](README.md)
**Code**: [server.py](server.py)

### I'm Debugging
**Start Here**: [README.md](README.md#troubleshooting)
**Run**: `./test_server.sh`
**Check**: [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md#troubleshooting-common-issues)

## By Task

### Installation
1. [QUICKSTART.md](QUICKSTART.md#step-by-step-setup) - Installation steps
2. Run `./setup.sh`
3. Run `./test_server.sh`

### Configuration
1. [QUICKSTART.md](QUICKSTART.md#5-configure-claude-code) - MCP config
2. [README.md](README.md#installation) - Detailed configuration

### Usage
1. [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - All usage patterns
2. [README.md](README.md#usage) - Basic usage

### Troubleshooting
1. [QUICKSTART.md](QUICKSTART.md#common-first-time-issues) - First-time issues
2. [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md#troubleshooting-common-issues) - Common problems
3. [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md#troubleshooting-migration-issues) - Migration issues

### Performance Tuning
1. [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md#performance-optimization) - Optimization tips
2. [README.md](README.md#model-information) - Model selection guide
3. [ARCHITECTURE.md](ARCHITECTURE.md#performance-characteristics) - Performance details

## Documentation Files

| File | Purpose | When to Read |
|------|---------|-------------|
| [INDEX.md](INDEX.md) | This file - navigation guide | Finding docs |
| [QUICKSTART.md](QUICKSTART.md) | Fast setup guide | First installation |
| [README.md](README.md) | Complete documentation | General reference |
| [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) | Detailed examples | Learning to use |
| [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) | Migration from Google | Switching servers |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Technical details | Understanding internals |
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | Project overview | High-level view |

## Code Files

| File | Purpose |
|------|---------|
| [server.py](server.py) | Main MCP server implementation |
| [requirements.txt](requirements.txt) | Python dependencies |
| [setup.sh](setup.sh) | Installation automation |
| [test_server.sh](test_server.sh) | Testing and verification |
| [.gitignore](.gitignore) | Git ignore patterns |

## Quick Links

### Common Tasks

**Install**: `./setup.sh`
**Test**: `./test_server.sh`
**Run**: `python3 server.py`

### Troubleshooting

**List microphones**:
```bash
python3 -c "import speech_recognition as sr; print('\n'.join(sr.Microphone.list_microphone_names()))"
```

**Check dependencies**:
```bash
python3 -c "import speech_recognition, whisper, numpy; print('All OK')"
```

**View logs**:
```bash
python3 server.py 2>&1 | tee debug.log
```

### Configuration

**MCP config location**: `~/.config/claude-code/mcp.json`

**Add server**:
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

## Documentation Reading Order

### First Time User

1. [QUICKSTART.md](QUICKSTART.md) - Get it installed
2. [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - Learn to use it
3. [README.md](README.md) - Reference as needed

### Migrating User

1. [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - Migration steps
2. [QUICKSTART.md](QUICKSTART.md) - Setup verification
3. [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - Learn new features

### Developer

1. [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Project overview
2. [ARCHITECTURE.md](ARCHITECTURE.md) - Technical design
3. [server.py](server.py) - Source code
4. [README.md](README.md) - API reference

## By Document Length

**Quick Read** (5 min):
- [QUICKSTART.md](QUICKSTART.md) - 300 lines
- [README.md](README.md) - 250 lines

**Medium Read** (15 min):
- [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) - 350 lines
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - 400 lines
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - 400 lines

**Deep Read** (30 min):
- [ARCHITECTURE.md](ARCHITECTURE.md) - 650 lines
- [server.py](server.py) - 400 lines

## FAQ

### Where do I start?
**[QUICKSTART.md](QUICKSTART.md)** - Always start here

### How do I use this?
**[USAGE_EXAMPLES.md](USAGE_EXAMPLES.md)** - Detailed examples

### What if something breaks?
**[README.md](README.md#troubleshooting)** - Troubleshooting section

### How do I switch from Google Speech?
**[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** - Complete migration guide

### How does it work internally?
**[ARCHITECTURE.md](ARCHITECTURE.md)** - Technical deep-dive

### What's the big picture?
**[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Project overview

## Getting Help

1. **Check docs** - Use this index to find the right guide
2. **Run tests** - `./test_server.sh` diagnoses issues
3. **Read logs** - `python3 server.py 2>&1 | tee debug.log`
4. **Check examples** - [USAGE_EXAMPLES.md](USAGE_EXAMPLES.md) has solutions

## External Resources

- **Whisper**: https://github.com/openai/whisper
- **MCP Protocol**: https://modelcontextprotocol.io
- **SpeechRecognition**: https://github.com/Uberi/speech_recognition

## Version Info

**Server Version**: 1.0.0
**MCP Protocol**: 2024-11-05
**Documentation**: Complete (2,000+ lines)

---

**Lost?** Start with [QUICKSTART.md](QUICKSTART.md)

**Ready?** Run `./setup.sh` to begin!
