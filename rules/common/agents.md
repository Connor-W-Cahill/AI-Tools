# Agent Orchestration Rules

## Available Specialized Agents

Global (in `~/.claude/agents/`):

| Agent | Purpose | When to Use |
|-------|---------|-------------|
| `planner` | Implementation planning with phase breakdown | Complex features, refactoring, multi-file changes |
| `architect` | System design, ADRs, trade-off analysis | Architectural decisions, new systems |
| `tdd-guide` | Test-driven development enforcement | New features, bug fixes — write tests FIRST |
| `code-reviewer` | Quality/security review (confidence >80%) | After writing or modifying code |
| `security-reviewer` | OWASP Top 10, secrets, injection, auth | Before commits to auth/API/input code |
| `spec-agent` | Spec-driven design (requirements → design → tasks) | Complex features needing structured planning |

Project (in `agents/` or `hub/` roles):

| Agent | Purpose |
|-------|---------|
| `multi-agent-orchestrator` | Coordinate multiple AI tools |
| `parallel-orchestrator` | Parallelize independent workstreams |
| `deep-research-expert` | Comprehensive research and analysis |
| `docs-writer` | Documentation creation/update |

## Proactive Agent Usage (No User Prompt Needed)

Use agents without waiting:
1. Complex feature request → **planner**
2. Code just written/modified → **code-reviewer**
3. Bug fix or new feature → **tdd-guide**
4. Architectural decision → **architect**
5. Auth/API/input code → **security-reviewer**

## Parallel Execution

Always launch independent agents in parallel:

```
# GOOD: Launch 3 agents simultaneously
- Agent 1: Security review of auth module
- Agent 2: Code review of new feature
- Agent 3: TDD check on utilities

# BAD: Sequential when not dependent
Run agent 1, wait, run agent 2, wait, run agent 3
```

## Slash Commands

- `/plan` — Plan before implementing (WAITS for confirmation)
- `/review` — Comprehensive code review
- `/tdd` — TDD workflow enforcement
- `/secure` — Security checklist and scan
- `/build-fix` — Fix build/type errors
