# AI-Tools

Portable multi-AI orchestration environment. Clone + `./setup.sh` = working AI dev setup.

## Quick Start

```bash
git clone <this-repo> ~/AI-Tools
cd ~/AI-Tools
./setup.sh          # Symlinks, deps, config
./setup.sh --voice  # Also install Jarvis voice assistant
```

## Components

| Directory | What |
|-----------|------|
| `orchestrator/` | Multi-AI coordination — `aio` CLI for registering, claiming files, heartbeats, handoffs |
| `hub/` | `ai` — mobile-SSH-friendly launcher with ultra-short subcommands (`ai c` = Claude, `ai s` = status) |
| `mcp-servers/` | MCP servers: `whisper-voice` (local speech-to-text), `task-state` (task coordination) |
| `agents/` | Shared agent definitions (15 specialized agents for orchestration, research, docs, etc.) |
| `voice-interface/` | Jarvis — wake-word-activated voice assistant with Codex brain, TTS, screen awareness |
| `config/` | Templates for AI tool configs (OpenCode, Ralph orchestrator) |
| `prompts/` | System prompts for AI tools |
| `docs/` | Project documentation |
| `.beads/` | Task tracking database (bd) |

## Prerequisites

- **Claude Code**: `npm install -g @anthropic-ai/claude-code`
- **Codex CLI**: `npm install -g @openai/codex`
- **Gemini CLI**: `npm install -g @anthropic-ai/gemini` (or via pipx)
- **Python 3.10+**: For MCP servers and voice interface
- **tmux**: For multi-pane AI sessions
- **jq**: For state file parsing

## Installing bd (Beads Task Tracker)

`bd` is a ~33MB binary not tracked in git. Install it:

```bash
# Download latest release
curl -fsSL https://github.com/beads-project/beads/releases/latest/download/bd-linux-amd64 \
  -o ~/.local/bin/bd
chmod +x ~/.local/bin/bd

# Verify
bd --version
```

## The `ai` Hub

Ultra-short commands for SSH from a phone:

```
ai s        Status dashboard (AIs + tasks + tmux)
ai c        Launch Claude (auto register/unregister)
ai x        Launch Codex
ai g        Launch Gemini
ai r        Ready tasks
ai t ID     Take a task
ai d ID     Done — close task
ai n words  New task
ai w        List tmux windows
ai p N      Peek at pane N
ai ?        Full help
```

## Multi-AI Orchestration

The `orchestrator/` provides file-level coordination between AI tools:

```bash
orchestrator/bin/aio status       # Who's active?
orchestrator/bin/aio register X   # Register tool X
orchestrator/bin/aio claim file path  # Claim a file
orchestrator/bin/aio release all  # Release claims
```

Each AI tool's instruction file (`CLAUDE.md`, `GEMINI.md`) tells it to check claims before editing.

## Voice Interface (Jarvis)

Wake-word activated voice assistant. See `voice-interface/README.md` for details.

```bash
./setup.sh --voice
systemctl --user enable --now voice-orchestrator.service
```

- Wake word: "Hey Jarvis"
- Hotkey: `Super+Shift+V`
- Brain: Codex CLI
- TTS: edge-tts (Ryan Neural voice)
