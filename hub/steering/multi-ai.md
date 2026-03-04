# Multi-AI Coordination Steering

## Context
Use when multiple AI tools (Claude, Codex, Gemini, Amp, OpenCode) may be working simultaneously.

## Coordination Protocol (aio)
```bash
orchestrator/bin/aio status           # Check who's active and what's claimed
orchestrator/bin/aio register claude  # Register before working
orchestrator/bin/aio claim file <path> # Claim a file before editing
orchestrator/bin/aio release all      # Release when done
orchestrator/bin/aio-context handoff "summary"  # Leave notes for next AI
```

## Tool Strengths (for delegation)
| Tool | Best for |
|------|----------|
| Claude (`ai c`) | Complex reasoning, code review, writing, planning |
| Codex (`ai x`) | Agentic execution, desktop control, terminal tasks |
| Gemini (`ai g`) | Long documents, web search, multi-modal |
| Aider (`ai ad`) | Git-aware coding with architect/editor mode |
| OpenCode (`ai o`) | Alternative code agent |
| Qwen (`ai q`) | Fast local model for simple tasks |

## Task Batching (from Augment best practice)
- When closing one task and starting another, do it atomically:
  `bd close <prev> && bd update <next> --status=in_progress`
- Subtask sizing: ~20 min chunks of coding work

## Context Sharing
- Shared context: `hub/context/current.md`
- AI-specific memories: `hub/memory/*.md`
- Handoff notes auto-persist in `orchestrator/context/`
- RAG: `python3 ~/AI-Tools/rag/knowledge_base.py search "<query>"`
