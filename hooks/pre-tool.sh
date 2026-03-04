#!/bin/bash
# hooks/pre-tool.sh — Safety check before Bash tool execution
# Reads JSON from stdin, warns on dangerous patterns, passes through.
# Exit code 0 = allow, 2 = block

set -e
input=$(cat)

# Extract command from JSON
cmd=$(echo "$input" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('command', ''))
except:
    pass
" 2>/dev/null || echo "")

# Warn on dangerous patterns (but allow — user approved full-access mode)
if echo "$cmd" | grep -qE 'rm -rf /|DROP TABLE|format '; then
  echo "[Hook] WARNING: Potentially destructive command detected" >&2
fi

# Suggest tmux for long-running commands
if [ -z "${TMUX:-}" ] && echo "$cmd" | grep -qE 'pytest|docker|make |pip install'; then
  echo "[Hook] Tip: Consider running in tmux for session persistence" >&2
fi

echo "$input"
exit 0
