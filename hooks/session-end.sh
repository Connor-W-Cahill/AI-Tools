#!/bin/bash
# hooks/session-end.sh — Auto-called by Claude Code Stop hook
# Silently logs session end + syncs beads. Target runtime: <3 seconds.

PROJECT_DIR="/home/connor/AI-Tools"
SESSIONS_DIR="$PROJECT_DIR/memory/sessions"
TODAY="$(date +%Y-%m-%d)"
SESSION_FILE="$SESSIONS_DIR/$TODAY.md"

# 1. Log session timestamp
mkdir -p "$SESSIONS_DIR"
if [ ! -f "$SESSION_FILE" ]; then
  echo "# Session Log — $TODAY" > "$SESSION_FILE"
fi
echo "- $(date +%H:%M) session end" >> "$SESSION_FILE"

# 2. Sync beads silently (non-fatal)
if command -v bd &>/dev/null; then
  bd sync --flush-only 2>/dev/null || true
fi

# 3. Commit memory/sessions if changed (non-fatal)
cd "$PROJECT_DIR"
if ! git diff --quiet memory/sessions/ 2>/dev/null; then
  git add memory/sessions/ 2>/dev/null && \
  git commit -m "chore: session log $(date +%Y-%m-%d) [skip ci]" 2>/dev/null || true
fi

exit 0
