# AI-Tools Skills (Agents)

Last updated: 2026-03-03

This file lists the shared skills available to all AI tools in this repo. Use the matching agent when a task fits the description. Source definitions live in `agents/*.md`.

## Steering Files
Load these at session start to inject relevant context:
- `hub/steering/devops.md` — systemd, Docker, Bash, infra work
- `hub/steering/python.md` — Python scripts and services
- `hub/steering/research.md` — papers, analysis, academic work
- `hub/steering/spec.md` — spec-driven feature design
- `hub/steering/multi-ai.md` — multi-AI coordination

## Spec-Driven Development
For complex features: use `spec-agent` or follow `hub/runbooks/spec-workflow.md`
- Creates `.specs/<feature>/requirements.md` → `design.md` → `tasks.md`
- Phases gate on explicit approval before advancing

Skills
- `ai-cli-sync` — Keep Codex, OpenCode, Gemini, and docs in sync. Source: `agents/ai-cli-sync.md`.
- `ai-error-resolver` — Document and resolve AI-generated errors, build a reusable error log. Source: `agents/ai-error-resolver.md`.
- `context-keeper` — Store and retrieve long-lived project decisions and preferences. Source: `agents/context-keeper.md`.
- `context-optimizer` — Compact context and plan token-efficient, multi-step work. Source: `agents/context-optimizer.md`.
- `deep-research-expert` — Provide deep, sourced explanations and analysis. Source: `agents/deep-research-expert.md`.
- `docs-writer` — Create or update documentation and technical writing. Source: `agents/docs-writer.md`.
- `git-repo-organizer` — Handle repo organization and git operations. Source: `agents/git-repo-organizer.md`.
- `instance-coordinator` — Coordinate multiple Codex CLI instances to avoid overlap. Source: `agents/instance-coordinator.md`.
- `mcp-server-architect` — Design or evaluate MCP servers and integrations. Source: `agents/mcp-server-architect.md`.
- `multi-agent-orchestrator` — Coordinate multiple AI tools for complex tasks. Source: `agents/multi-agent-orchestrator.md`.
- `n8n-workflow-automator` — Design and implement automation workflows. Source: `agents/n8n-workflow-automator.md`.
- `parallel-orchestrator` — Run parallel Codex instances for independent workstreams. Source: `agents/parallel-orchestrator.md`.
- `productivity-suite-navigator` — Access Google/Proton productivity suites for context. Source: `agents/productivity-suite-navigator.md`.
- `project-orchestrator` — Plan new projects and recommend agent/tool usage. Source: `agents/project-orchestrator.md`.
- `spec-agent` — Spec-driven development: Requirements → Design → Tasks before coding. Source: `agents/spec-agent.md`.
- `web-navigator` — Perform authenticated web tasks and data extraction. Source: `agents/web-navigator.md`.

External Skills (Composio Awesome Claude Skills)
These are recommended additions for general dev workflows. Install from the ComposioHQ list.
- `artifacts-builder` — Build rich Claude artifacts with modern frontend stacks.
- `changelog-generator` — Create user-facing changelogs from git history.
- `file-organizer` — Organize files and folders based on context.
- `mcp-builder` — Build and maintain MCP servers.
