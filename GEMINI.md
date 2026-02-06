# AI-Tools — Multi-AI Orchestration

This project coordinates Claude, Codex, Gemini, and Amp.

**Required before editing:**
```bash
orchestrator/bin/aio status
orchestrator/bin/aio register gemini
orchestrator/bin/aio claim file <path>
```

**When done:**
```bash
orchestrator/bin/aio release all
orchestrator/bin/aio unregister
```

## Project Layout

- `orchestrator/` — Multi-AI coordination (aio CLI, hooks, integrations)
- `hub/` — `ai` mobile-SSH launcher script + bash completions
- `mcp-servers/` — MCP servers (whisper-voice, task-state)
- `agents/` — Shared agent definitions (*.md)
- `config/` — Templates for AI tool configs
- `voice-interface/` — Jarvis voice assistant daemon
