# Hub Steering Files

Steering files inject additional context into AI sessions based on what you're working on.
Inspired by Kiro's steering system.

## How to Use

Reference a steering file at the start of a session or task:
```bash
cat hub/steering/devops.md   # Read context for infra work
cat hub/steering/python.md   # Read context for Python projects
cat hub/steering/research.md # Read context for papers/research
cat hub/steering/spec.md     # Read context for spec-driven features
```

Or paste the contents into your AI session when starting that type of work.

## Files

| File | Use when... |
|------|-------------|
| `devops.md` | Working on systemd, Docker, Bash, infra |
| `python.md` | Working on Python scripts or services |
| `research.md` | Writing papers, research briefs, analysis |
| `spec.md` | Designing a complex feature from scratch |
| `multi-ai.md` | Coordinating across multiple AI tools |

## Auto-Inclusion (Future)

When a Claude Code hook or hub/ai launcher supports it, these will auto-inject
based on the files open or task type detected.
