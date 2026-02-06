#!/usr/bin/env bash
#
# beads-sync - Sync beads issues with AI orchestrator
# Links bd issues to AI instance claims
#
# Usage:
#   beads-sync start <issue-id>    - Claim issue and mark in_progress
#   beads-sync done <issue-id>     - Release and close issue
#   beads-sync status              - Show beads + orchestrator status
#   beads-sync available           - Show issues ready for AI work

set -euo pipefail

AIO_DIR="${AIO_DIR:-$HOME/.ai-orchestrator}"
export PATH="$AIO_DIR/bin:$PATH"

# Start working on an issue
cmd_start() {
    local issue="$1"

    # Claim the issue in orchestrator
    if ! aio claim task "$issue" 2>/dev/null; then
        echo "Issue $issue is already claimed by another AI"
        aio check "task:$issue" 2>/dev/null || true
        exit 1
    fi

    # Update beads
    bd update "$issue" --status=in_progress

    # Update orchestrator task
    local title=$(bd show "$issue" 2>/dev/null | grep "Title:" | sed 's/.*Title: //')
    aio task "$title" "$issue"

    echo "Started: $issue - $title"
}

# Complete an issue
cmd_done() {
    local issue="$1"
    local reason="${2:-Completed}"

    # Close beads issue
    bd close "$issue" --reason="$reason"

    # Release the claim
    local claim_id=$(aio status 2>/dev/null | grep -A1 "\[task\] $issue" | head -1 | awk '{print $2}' || echo "")
    if [[ -n "$claim_id" ]]; then
        aio release "$claim_id" 2>/dev/null || true
    fi

    # Clear task
    aio task ""

    echo "Completed: $issue"
}

# Show combined status
cmd_status() {
    echo "=== Beads Issues ==="
    bd list --status=open 2>/dev/null || echo "No open issues"
    echo ""
    echo "=== Orchestrator Status ==="
    aio status 2>/dev/null || echo "No active instances"
}

# Show available issues (not blocked, not claimed)
cmd_available() {
    echo "=== Available Issues ==="

    # Get ready issues from beads
    local ready=$(bd ready 2>/dev/null)

    if [[ -z "$ready" || "$ready" == *"No open issues"* ]]; then
        echo "No issues available"
        return
    fi

    # Filter out claimed issues
    echo "$ready" | while read -r line; do
        local issue_id=$(echo "$line" | grep -oE '\b[A-Za-z]+-[A-Za-z0-9]+\b' | head -1)
        if [[ -n "$issue_id" ]]; then
            if aio check "task:$issue_id" >/dev/null 2>&1; then
                echo "$line"
            else
                echo "$line [CLAIMED]"
            fi
        else
            echo "$line"
        fi
    done
}

# Main
main() {
    local cmd="${1:-status}"
    shift || true

    case "$cmd" in
        start)    cmd_start "$@" ;;
        done)     cmd_done "$@" ;;
        status)   cmd_status ;;
        available) cmd_available ;;
        *)
            echo "Usage: beads-sync <start|done|status|available> [issue-id]"
            ;;
    esac
}

main "$@"
