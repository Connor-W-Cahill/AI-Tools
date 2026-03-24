# AI-Tools — Multi-AI Orchestration Workspace

## Memory Protocol

Memory auto-loads from `memory/MEMORY.md` each session (symlinked from Claude Code auto-memory).

- **Add a fact**: `tools/memory add "key: value"`
- **Search history**: `python3 rag/knowledge_base.py search "<query>"`
- **End session**: `tools/sync` (logs session, syncs beads, commits memory)

## AI Launcher

```bash
ai c        # Claude Code (full permissions)
ai x        # Codex CLI
ai g        # Gemini CLI
ai q        # Qwen/Ollama (local)
ai o        # OpenCode (model router via LiteLLM)
ai ad       # Aider
ai ?        # Help
```

## Jira Integration (Required)

When the user mentions a Jira task, ticket, board, or project — **always** use the Jira CLI:

```bash
python3 tools/jira route "description"        # check which project it routes to
python3 tools/jira create "task description"  # create ticket (auto-routes + syncs beads)
python3 tools/jira issues [PROJECT]           # list issues
python3 tools/jira view PROJ-123              # view a ticket
python3 tools/jira open PROJ-123              # open in browser
python3 tools/jira sync                       # pull all assigned Jira + Confluence tasks → beads
python3 tools/jira start PROJ-123             # Jira → In Progress + beads in_progress
python3 tools/jira done PROJ-123              # Jira → Done + beads closed
```

**Projects** (auto-routing by keyword):
| Key | Purpose |
|-----|---------|
| CYBPROX | Proxmox cluster, VMs, nodes, LVM, storage |
| PXELAND | PXE boot, DHCP, OS images, network boot |
| CYBVPN | VPN, remote access, network config |
| CYBPACK | Packer image building, VM templates |
| CYBCSSP | CSSP security platform, VPC, cloud instances |
| LOUD | Lab ops, AWX/Ansible, AER lab machines |
| STATLERITS | Statler ITS helpdesk (printers, projectors, software) |
| INVTY2025 | IT asset inventory, hardware tracking |
| CYB | General cybereers (SSH, RDP, troubleshooting, CTF) |

**Rules:**
- Creating a Jira ticket ALWAYS also creates a beads issue (auto-synced)
- `jira sync` pulls ALL assigned open Jira issues + Confluence tasks into beads (idempotent)
- `jira start`/`jira done` transition both Jira and beads simultaneously
- Use `jira route "..."` to verify routing before creating if unsure
- Config: `~/.config/jira/config.json` | Tokens: `~/.config/jira/tokens.json`
- Re-auth if token expires: `python3 tools/jira auth`

## Task Tracking (Required)

Use beads for ALL task tracking:
```bash
bd ready                              # Find available work
bd create --title="..." --type=task --priority=2
bd update <id> --status=in_progress
bd close <id>
bd sync                               # Sync at session end
```
**Never use**: TodoWrite, TaskCreate, or markdown TODO files.

## Local AI Infrastructure

| Service | URL | Purpose |
|---------|-----|---------|
| LiteLLM Proxy | http://localhost:4000 | Unified API (Claude, GPT-4o, Ollama) |
| Ollama | http://localhost:11434 | Local LLM (qwen2.5:3b) |
| Open WebUI | http://localhost:3000 | Chat UI |
| Langfuse | http://localhost:3001 | LLM observability |
| n8n | http://localhost:5678 | Workflow automation |

RAG search: `python3 rag/knowledge_base.py search "<query>"`

## Project Layout

```
tools/          AI launcher (tools/ai) + memory + sync scripts
hooks/          Claude Code lifecycle hooks (Stop → session-end.sh)
agents/         Agent definitions (planner, code-reviewer, architect, etc.)
skills/         Domain knowledge (tdd-workflow, python-patterns, security-review)
rules/common/   Coding guidelines (coding-style, security, testing, git-workflow)
rules/steering/ Context injection (devops.md, python.md, research.md, spec.md)
memory/         Persistent memory (MEMORY.md + sessions/)
docs/           Architecture, runbooks, getting-started
mcp-servers/    MCP servers (whisper-voice, task-state)
voice-interface/ Jarvis voice assistant daemon
rag/            ChromaDB RAG knowledge base
litellm/        LiteLLM proxy config + systemd service
langfuse/       Langfuse Docker Compose
n8n/            n8n workflow automation
.beads/         Task tracking (bd)
```

## Quality Rules

Load steering files for domain-specific context:
```bash
cat rules/steering/devops.md     # infra, systemd, Docker
cat rules/steering/python.md     # Python services/scripts
cat rules/steering/research.md   # papers, academic work
cat rules/steering/spec.md       # spec-driven feature design
```

Rules in `rules/common/`:
- `coding-style.md` — Immutability (CRITICAL), file size ≤800 lines
- `security.md` — Pre-commit checklist; STOP on CRITICAL findings
- `testing.md` — TDD: write failing test FIRST, 80%+ coverage
- `git-workflow.md` — Commit format: `<type>: <description>`
- `agents.md` — When to use each agent proactively

## Coding Best Practices

1. **Before editing**: `git log --oneline -10 -- <path>` to check history
2. **Before submitting**: run lint and tests; no `console.log`/debug output
3. **Never modify tests** to pass — fix the code under test
4. **Fix root cause**, not symptoms
5. **Immutability**: always create new objects, never mutate in-place
6. **File size**: 200-400 lines typical, 800 max

## Proactive Agent Usage

Use these WITHOUT waiting for user to ask:
- Complex feature → run `planner` agent first
- Code written/modified → run `code-reviewer` agent
- New feature or bug fix → use `/tdd` workflow
- Architectural decision → run `architect` agent
- Auth/API/user-input code → run `security-reviewer`

## Slash Commands

- `/plan` — Plan before implementing (waits for confirmation)
- `/review` — Confidence-based code review
- `/tdd` — Test-driven development workflow
- `/secure` — Security scan
- `/build-fix` — Fix build errors

## Spec-Driven Development

For complex features (3+ files, ambiguous requirements, multi-session work):
1. Specs live in `.specs/<feature-name>/` (requirements → design → tasks)
2. See `docs/runbooks/spec-workflow.md` for the full workflow
3. Never code before specs are approved

## Session Close Protocol

Before saying "done", run:
```bash
git status && git add <files>
bd sync
git commit -m "<type>: <description>"
git push
```

## Skills (Agents)

See `AGENTS.md` for the full catalog.
