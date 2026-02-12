#!/usr/bin/env bash
set -euo pipefail

HUB_DIR="${HUB_DIR:-/home/connor/AI-Tools/hub}"
TITLE="$*"

if [ -z "$TITLE" ]; then
  echo "usage: start-task <title>" >&2
  exit 1
fi

slug=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/^-//;s/-$//')
DATE_STR=$(date -u +"%Y%m%d")
FILE="${HUB_DIR}/runbooks/${DATE_STR}-${slug}.md"

if [ -f "$FILE" ]; then
  echo "Already exists: $FILE" >&2
  exit 1
fi

sed "s/^# Runbook/# Runbook: ${TITLE}/" "${HUB_DIR}/templates/runbook.md" > "$FILE"

# add to active projects list
printf "- %s (%s)\n" "$TITLE" "$FILE" >> "${HUB_DIR}/projects/active.md"

echo "Created $FILE"
