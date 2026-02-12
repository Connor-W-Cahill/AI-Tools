#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${HUB_DIR:-/home/connor/AI-Tools/hub}"
CATEGORY="${1:-}"
shift || true
TEXT="$*"

if [ -z "$CATEGORY" ] || [ -z "$TEXT" ]; then
  echo "usage: add-memory <category> <text>" >&2
  echo "categories: decision|learning|warning|pattern|handoff|note" >&2
  exit 1
fi

stamp=$(date -u +"%Y-%m-%d")

# append to global memory
{
  echo "- [${stamp}] (${CATEGORY}) ${TEXT}"
} >> "${HUB_DIR}/memory/global.md"

# also add to aio-context if category is supported
case "$CATEGORY" in
  decision|learning|warning|pattern|handoff)
    if command -v /home/connor/AI-Tools/orchestrator/bin/aio-context >/dev/null 2>&1; then
      /home/connor/AI-Tools/orchestrator/bin/aio-context "$CATEGORY" "$TEXT" || true
    fi
    ;;
  note)
    ;;
  *)
    ;;
 esac

echo "Added memory (${CATEGORY})"
