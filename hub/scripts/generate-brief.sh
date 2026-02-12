#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${HUB_DIR:-/home/connor/AI-Tools/hub}"
OUT_FILE="${HUB_DIR}/context/current.md"
DATE_STR=$(date -u +"%Y-%m-%d")

max_lines() {
  local n="$1"
  shift
  if [ -f "$1" ]; then
    head -n "$n" "$1"
  fi
}

{
  echo "# Daily Brief (${DATE_STR} UTC)"
  echo ""

  echo "## Priorities"
  max_lines 200 "${HUB_DIR}/context/priorities.md" | sed '1d' || true
  echo ""

  echo "## Active Projects"
  max_lines 200 "${HUB_DIR}/projects/active.md" | sed '1d' || true
  echo ""

  echo "## Preferences"
  max_lines 200 "${HUB_DIR}/memory/preferences.md" | sed '1d' || true
  echo ""

  echo "## Key Memory"
  max_lines 200 "${HUB_DIR}/memory/global.md" | sed '1d' || true
  echo ""

  echo "## Environment"
  max_lines 200 "${HUB_DIR}/memory/devices.md" | sed '1d' || true
  echo ""

  echo "## Recent AIO Context"
  if command -v /home/connor/AI-Tools/orchestrator/bin/aio-context >/dev/null 2>&1; then
    /home/connor/AI-Tools/orchestrator/bin/aio-context export | head -n 200
  else
    echo "(aio-context not available)"
  fi
  echo ""

  echo "## Active Tasks (beads)"
  if command -v bd >/dev/null 2>&1; then
    bd list --status=in_progress 2>/dev/null | head -n 50 || true
    bd list --status=open 2>/dev/null | head -n 50 || true
  else
    echo "(bd not available)"
  fi
} > "$OUT_FILE"

echo "Wrote ${OUT_FILE}"
