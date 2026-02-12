# AI-Tools — Multi-AI Orchestration

This project coordinates Claude, Codex, Gemini, and Amp.

## Hub Context (Required)

All AI tools must use the Hub as the source of truth:
- Context file: `hub/context/current.md`
- Memory store: `hub/memory/*.md`
- Workflows/templates: `hub/templates/` and `hub/runbooks/`

Always launch via `hub/ai` or the context-aware wrappers:
```bash
ai x        # Codex with Hub context
ai c        # Claude with Hub context
ai g        # Gemini with Hub context
ai b        # Generate fresh daily brief
```

## GitHub Workflow (Required)

Use GitHub for all tracked work:
- Create issues for tasks
- Use branches for changes
- Open PRs for reviews/merges

**Required before editing:**
```bash
orchestrator/bin/aio status
orchestrator/bin/aio register codex
orchestrator/bin/aio claim file <path>
```

**When done:**
```bash
orchestrator/bin/aio release all
orchestrator/bin/aio unregister
```

## Local AI Infrastructure

Available services:

| Service | URL | Purpose |
|---|---|---|
| **LiteLLM Proxy** | `http://localhost:4000` | Unified API — routes to Claude, GPT-4o, Ollama with fallback chains |
| **Ollama** | `http://localhost:11434` | Local LLM (qwen2.5:3b) on GPU, embedding model |
| **Open WebUI** | `http://localhost:3000` | Chat UI for Ollama models |
| **Langfuse** | `http://localhost:3001` | LLM observability dashboard |
| **n8n** | `http://localhost:5678` | Workflow automation |

### RAG Knowledge Base
Search project history semantically:
```bash
python3 ~/AI-Tools/rag/knowledge_base.py search "<query>"
```

## Project Layout

- `orchestrator/` — Multi-AI coordination (aio CLI, hooks, integrations)
- `hub/` — Context-aware AI launcher, memory, templates, runbooks
- `mcp-servers/` — MCP servers (whisper-voice, task-state)
- `agents/` — Shared agent definitions (*.md)
- `config/` — Templates for AI tool configs
- `voice-interface/` — Jarvis voice assistant daemon
- `rag/` — ChromaDB RAG knowledge base
- `litellm/` — LiteLLM proxy config
- `langfuse/` — Langfuse Docker Compose
- `n8n/` — n8n workflow data

## Skills (Agents)

Use the shared skills catalog in `AGENTS.md` to pick the right specialist for a task.
