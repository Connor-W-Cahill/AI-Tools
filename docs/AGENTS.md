# Agents

This workspace mirrors the Codex agent setup for OpenCode and Codex use.

## Source
- Codex agents copied from `~/.codex/agents`
- Codex settings copied to `.opencode/claude-settings.json` and `.opencode/claude-settings.local.json` (legacy filenames)
- OpenCode agents mirrored in `.opencode/agents`
- Codex agents mirrored in `.codex/agents`

## Agents
- ai-cli-sync
- ai-error-resolver
- context-keeper
- context-optimizer
- deep-research-expert
- docs-writer
- git-repo-organizer
- instance-coordinator
- mcp-server-architect
- multi-agent-orchestrator
- n8n-workflow-automator
- parallel-orchestrator
- productivity-suite-navigator
- project-orchestrator
- web-navigator

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
Use 'bd' for task tracking

# Multi-AI Orchestration

**Coordination required** - Claude, Gemini, Amp may be active.

Before work: `~/.ai-orchestrator/bin/aio register codex && aio status`
Before edits: `~/.ai-orchestrator/bin/aio claim file <path>`
When done: `~/.ai-orchestrator/bin/aio release all && aio unregister`

Never edit files claimed by other AIs.
