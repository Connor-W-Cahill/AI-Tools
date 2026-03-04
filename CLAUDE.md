# AI-Tools — Multi-AI Orchestration

**This project uses multi-AI coordination.** Other AI tools (Codex, Gemini, Amp) may be active.

## Hub Context (Required)

All AI tools must use the Hub as the source of truth:
- Context file: `hub/context/current.md`
- Memory store: `hub/memory/*.md`
- Workflows/templates: `hub/templates/` and `hub/runbooks/`

Always launch via `hub/ai` or the context-aware wrappers:
```bash
ai c        # Claude with Hub context
ai x        # Codex with Hub context
ai g        # Gemini with Hub context
ai b        # Generate fresh daily brief
```

## GitHub Workflow (Required)

Use GitHub for all tracked work:
- Create issues for tasks
- Use branches for changes
- Open PRs for reviews/merges

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

## Local AI Infrastructure

Available services for all agents to use:

| Service | URL | Purpose |
|---|---|---|
| **LiteLLM Proxy** | `http://localhost:4000` | Unified API — routes to Claude, GPT-4o, Ollama with fallback chains |
| **Ollama** | `http://localhost:11434` | Local LLM (qwen2.5:3b) on GPU, embedding model (nomic-embed-text) |
| **Open WebUI** | `http://localhost:3000` | Chat UI for Ollama models |
| **Langfuse** | `http://localhost:3001` | LLM observability dashboard (auto-tracks LiteLLM requests) |
| **n8n** | `http://localhost:5678` | Workflow automation |

### Using LiteLLM Proxy
Any OpenAI-compatible client can use `http://localhost:4000/v1` as the base URL:
- Models: `claude-sonnet`, `claude-haiku`, `claude-opus`, `gpt-4o`, `gpt-4o-mini`, `qwen2.5:3b`
- No API key required (open proxy)

### RAG Knowledge Base
Search project history and documentation semantically:
```bash
python3 ~/AI-Tools/rag/knowledge_base.py search "<query>"
python3 ~/AI-Tools/rag/knowledge_base.py stats
python3 ~/AI-Tools/rag/knowledge_base.py reindex
```

## Project Layout

- `orchestrator/` — Multi-AI coordination (aio CLI, hooks, integrations)
- `hub/` — Context-aware AI launcher, memory, templates, runbooks
- `mcp-servers/` — MCP servers (whisper-voice, task-state)
- `agents/` — Shared agent definitions (*.md)
- `config/` — Templates for AI tool configs (opencode, ralph)
- `voice-interface/` — Jarvis voice assistant daemon
- `rag/` — ChromaDB RAG knowledge base
- `litellm/` — LiteLLM proxy config and env
- `langfuse/` — Langfuse Docker Compose
- `n8n/` — n8n workflow data
- `prompts/` — System prompts
- `docs/` — Project documentation
- `.beads/` — Task tracking (bd)

## Coding Best Practices

From studying leading AI coding agents (Devin, Augment, Cursor):

1. **Before editing similar code**: run `git log --oneline -10 -- <path>` and `git blame <file>` to understand prior decisions
2. **Before submitting changes**: run lint and tests if available
3. **Never modify tests** to make them pass — fix the code under test
4. **Fix root cause**, not symptoms (no workarounds for broken infra)
5. **Batch task transitions**: when closing one task and opening next, do it atomically

## Steering Files (Context Injection)

Load relevant steering files at session start for domain-specific context:
- `cat hub/steering/devops.md` — infra, systemd, Docker
- `cat hub/steering/python.md` — Python services/scripts
- `cat hub/steering/research.md` — papers, academic work
- `cat hub/steering/spec.md` — spec-driven feature design
- `cat hub/steering/multi-ai.md` — multi-AI coordination

## Spec-Driven Development

For complex features (3+ files, ambiguous requirements, multi-session work):
1. Use `spec-agent` or follow `hub/runbooks/spec-workflow.md`
2. Specs live in `.specs/<feature-name>/` (requirements → design → tasks)
3. Never code before specs are approved

## Skills (Agents)

Use the shared skills catalog in `AGENTS.md` to pick the right specialist for a task.
