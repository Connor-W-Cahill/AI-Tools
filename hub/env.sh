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

# Cost-tiered aider shortcuts (all route through LiteLLM on :4000)
alias ad-local='aider --model openai/qwen2.5:3b'       # FREE - local GPU
alias ad-cheap='aider --model openai/claude-haiku'      # ~$0.25/MTok
alias ad-smart='aider --model openai/claude-sonnet'     # ~$3/MTok
alias ad-max='aider --model openai/claude-opus'         # ~$15/MTok
