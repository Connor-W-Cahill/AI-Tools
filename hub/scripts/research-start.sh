#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${HUB_DIR:-/home/connor/AI-Tools/hub}"
TITLE="$*"

if [ -z "$TITLE" ]; then
  echo "usage: research-start <topic>" >&2
  exit 1
fi

slug=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')
DATE_STR=$(date -u +"%Y%m%d")
FILE="${HUB_DIR}/notes/research/${DATE_STR}-${slug}.md"

if [ -f "$FILE" ]; then
  echo "Already exists: $FILE" >&2
  exit 1
fi

sed "s/^# Research Brief/# Research Brief: ${TITLE}/" "${HUB_DIR}/templates/research-brief.md" > "$FILE"

printf "- Research: %s (%s)\n" "$TITLE" "$FILE" >> "${HUB_DIR}/projects/active.md"

echo "Created $FILE"
