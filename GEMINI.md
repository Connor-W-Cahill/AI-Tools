# AI-Tools — Multi-AI Orchestration

This project coordinates Claude, Codex, Gemini, and Amp.

## Hub Context (Required)

All AI tools must use the Hub as the source of truth:
- Context file: `hub/context/current.md`
- Memory store: `hub/memory/*.md`
- Workflows/templates: `hub/templates/` and `hub/runbooks/`

Always launch via `hub/ai` or the context-aware wrappers:
```bash
ai g        # Gemini with Hub context
ai c        # Claude with Hub context
ai x        # Codex with Hub context
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

## Skills (Agents)

Use the shared skills catalog in `AGENTS.md` to pick the right specialist for a task.
