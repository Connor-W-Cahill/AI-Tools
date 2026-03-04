# AI-Tools Architecture

## Overview

A unified workspace for multi-AI coordination with persistent memory,
local AI infrastructure, and automated lifecycle management.

```
┌─────────────────────────────────────────────────────┐
│                   AI Tools Hub                       │
│  claude code │ codex │ gemini │ opencode │ aider     │
└───────────────────────┬─────────────────────────────┘
                        │ tools/ai (launcher)
                        ▼
┌─────────────────────────────────────────────────────┐
│              LiteLLM Proxy (:4000)                   │
│  claude-sonnet │ gpt-4o │ qwen2.5:3b (ollama)        │
└───────────────────────┬─────────────────────────────┘
                        │
              ┌─────────┴──────────┐
              ▼                    ▼
         Anthropic API         Ollama (:11434)
                                   │
                              GTX 1050 Ti (4GB GPU)
```

## Key Components

### Memory System
- `memory/MEMORY.md` — primary persistent memory, symlinked to Claude Code auto-memory
- `hooks/session-end.sh` — fires on Claude Code Stop event, logs session + syncs
- `tools/sync` — manual session-end: memory log + bd sync + git commit
- `rag/` — ChromaDB semantic search over project history

### AI Infrastructure
- **LiteLLM**: unified OpenAI-compatible API, routes to Claude/GPT-4o/Ollama
- **Langfuse**: LLM observability dashboard, auto-tracks all LiteLLM requests
- **Ollama**: local GPU inference (qwen2.5:3b for fast/cheap, nomic-embed-text for RAG)
- **n8n**: workflow automation (webhooks, scheduled jobs)

### Voice (Jarvis)
- `voice-interface/orchestrator/` — systemd service (`voice-orchestrator.service`)
- Wake word: "Hey Jarvis" or `Super+Shift+V`
- Routes: simple intents → Ollama (fast), complex/action → Codex CLI

### Task Tracking
- **Beads** (`.beads/`) — all task management; `bd` CLI
- Never use markdown TODO files or TaskCreate

### Multi-AI Coordination
- `orchestrator/bin/aio` — register/claim/release coordination (still available)
- `hooks/` — lifecycle automation for Claude Code
- `memory/sessions/` — per-session activity logs

## Data Flow

```
User prompt → Claude Code
  → PreToolUse hook (safety check)
  → Tool execution
  → PostToolUse hook
  → Response
  → Stop hook → session-end.sh → bd sync + memory log
```

## Services Map

| Service | Start | Config |
|---------|-------|--------|
| LiteLLM | `systemctl --user start litellm` | `litellm/config.yaml` |
| Ollama | `systemctl start ollama` (system) | `/etc/ollama/` |
| Jarvis | `systemctl --user start voice-orchestrator` | `voice-interface/orchestrator/` |
| Open WebUI | `docker compose up` in `langfuse/` | `.env` |
| Langfuse | `docker compose up` in `langfuse/` | `.env` |
| n8n | `docker compose up` in `n8n/` | `n8n/data/` |
