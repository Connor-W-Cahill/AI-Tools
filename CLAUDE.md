# AI-Tools — Multi-AI Orchestration

**This project uses multi-AI coordination.** Other AI tools (Codex, Gemini, Amp) may be active.

## Before Editing Files

```bash
orchestrator/bin/aio status          # Check active AIs
orchestrator/bin/aio register claude  # Register yourself
orchestrator/bin/aio claim file <path>  # Claim before editing
```

## When Done

```bash
orchestrator/bin/aio release all
orchestrator/bin/aio-context handoff "summary"
orchestrator/bin/aio unregister
```

**Rule**: Never edit files claimed by other AIs. Check `aio status` first.

## Project Layout

- `orchestrator/` — Multi-AI coordination (aio CLI, hooks, integrations)
- `hub/` — `ai` mobile-SSH launcher script + bash completions
- `mcp-servers/` — MCP servers (whisper-voice, task-state)
- `agents/` — Shared agent definitions (*.md)
- `config/` — Templates for AI tool configs (opencode, ralph)
- `voice-interface/` — Jarvis voice assistant daemon
- `prompts/` — System prompts
- `docs/` — Project documentation
- `.beads/` — Task tracking (bd)
