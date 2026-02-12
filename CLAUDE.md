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

## Skills (Agents)

Use the shared skills catalog in `AGENTS.md` to pick the right specialist for a task.
