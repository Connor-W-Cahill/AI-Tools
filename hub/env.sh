#!/usr/bin/env bash
# AI-Tools Hub environment

export HUB_DIR="${HUB_DIR:-/home/connor/AI-Tools/hub}"

# Prefer context-aware wrappers
alias codex="${HUB_DIR}/scripts/codex-with-context"
alias claude="${HUB_DIR}/scripts/claude-with-context"
alias gemini="${HUB_DIR}/scripts/gemini-with-context"

# Helper aliases
alias ai-brief="${HUB_DIR}/scripts/generate-brief.sh"
alias ai-mem="${HUB_DIR}/scripts/add-memory.sh"
alias ai-task="${HUB_DIR}/scripts/start-task.sh"
alias ai-research="${HUB_DIR}/scripts/research-start.sh"
