# AI-Tools Project Memory

## Environment
- OS: Ubuntu Linux 5.15.0-139-generic
- GPU: NVIDIA GeForce GTX 1050 Ti (4GB VRAM), driver 575.57.08
- Workspace: /home/connor/AI-Tools
- Shell: bash, Python 3.8 (system) / 3.12 (litellm venv via uv)
- Tools: codex, claude code, gemini cli, aider, opencode

## Local AI Infrastructure
- **Ollama**: v0.15.6, localhost:11434, models: qwen2.5:3b, nomic-embed-text
- **LiteLLM**: v1.81.10 proxy on port 4000, venv at `litellm/.venv/`
  - Config: `litellm/config.yaml`, env: `litellm/env`
  - Service: `litellm.service` (systemd user unit)
  - Routes: claude-sonnet, claude-haiku, claude-opus, gpt-4o, gpt-4o-mini, qwen2.5:3b
- **Open WebUI**: Docker on port 3000
- **Langfuse**: Docker on port 3001 (LLM observability, integrated with LiteLLM)
- **n8n**: Docker on port 5678 (workflow automation)
- **Aider**: pip-installed, git-aware coding assistant (`ai ad` to launch)

## AI Launcher (`tools/ai`)
- `ai c` → Claude Code (full permissions)
- `ai x` → Codex CLI
- `ai g` → Gemini CLI
- `ai q` → Qwen/Ollama (local)
- `ai o` → OpenCode (model router)

## Voice Orchestrator (Jarvis) — `voice-interface/orchestrator/`
- **Service**: `voice-orchestrator.service` (systemd user unit, enabled)
- **Wake word**: "Hey Jarvis" via openwakeword (`hey_jarvis_v0.1`, threshold=0.35)
- **Hotkey**: `Super+Shift+V` → `touch /tmp/voice_orchestrator_trigger`
- **Brain**: Codex CLI (`codex exec --dangerously-bypass-approvals-and-sandbox`)
- **TTS**: edge-tts, `en-GB-RyanNeural`, pre-cached phrases
- **Transcription**: Whisper `base.en`
- **Local LLM routing**: simple/knowledge → Ollama qwen2.5:3b, complex/action → Codex
- **Old dispatcher**: `user-voice-interface.service` — DISABLED, replaced by orchestrator

## RAG Knowledge Base — `rag/knowledge_base.py`
- **Storage**: ChromaDB at `~/.local/share/ai-knowledge/`
- **Collections**: beads_tasks, aio_context, conversations, project_docs
- **CLI**: `python3 rag/knowledge_base.py [reindex|search <query>|stats]`
- **Python 3.8 fix**: `pysqlite3-binary` monkey-patch, `posthog<3.5.0`

## Key Patterns
- **Task tracking**: `bd` (beads) only — never TodoWrite/TaskCreate/markdown
- **Session close**: `bd sync` before done (or `tools/sync` for full save)
- **Service debugging**: `journalctl --user -u <service> --no-pager -n N`
- **Before editing**: `git log --oneline -10 -- <path>` to check history
- **Spec workflow**: complex features → `.specs/<feature>/` (docs/runbooks/spec-workflow.md)
- **Steering files**: `rules/steering/` — load devops.md, python.md as needed
- **Memory**: `tools/memory add "..."` to add facts, `tools/sync` to commit session log
- **Auto-memory**: memory/MEMORY.md is symlinked to ~/.claude/.../memory/MEMORY.md

## Project Structure (rebuilt 2026-03-03)
- `tools/` — ai launcher, memory, sync scripts
- `hooks/` — Claude Code Stop hook → session-end.sh
- `agents/` — planner, code-reviewer, architect, tdd-guide, security-reviewer
- `skills/` — tdd-workflow, python-patterns, security-review, coding-standards
- `rules/common/` — coding-style, security, testing, git-workflow, agents
- `rules/steering/` — devops, python, research, spec, multi-ai
- `memory/` — MEMORY.md + sessions/

## Preferences
- Writing: concise, pragmatic, actionable
- Code: simple, readable, well-tested, immutable patterns
- DevOps: include rollback + validation steps
- GitHub: issues + branches + PRs for tracked work
