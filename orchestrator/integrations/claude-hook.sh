#!/usr/bin/env bash
# Claude Code Integration Hook
# Source this in your shell or add to CLAUDE.md instructions

export PATH="$HOME/.ai-orchestrator/bin:$PATH"
export AIO_TOOL="claude"

# Auto-register on first use
_aio_ensure_registered() {
    if [[ ! -f "$HOME/.ai-orchestrator/.current_instance" ]] || \
       ! grep -q "^claude-" "$HOME/.ai-orchestrator/.current_instance" 2>/dev/null; then
        aio register claude "$(pwd)"
    fi
}

# Heartbeat function - call periodically
aio_heartbeat() {
    _aio_ensure_registered
    aio heartbeat >/dev/null 2>&1 &
}

# Claim a file before editing
aio_claim_file() {
    _aio_ensure_registered
    aio claim file "$1"
}

# Claim a directory
aio_claim_dir() {
    _aio_ensure_registered
    aio claim directory "$1"
}

# Check before editing
aio_safe_edit() {
    local file="$1"
    if aio check "$file" >/dev/null 2>&1; then
        return 0  # Available
    else
        echo "WARNING: $file is claimed by another AI instance"
        return 1
    fi
}

# Release all and unregister on exit
aio_cleanup() {
    aio unregister 2>/dev/null || true
}

# Set trap for cleanup
trap aio_cleanup EXIT

# Export functions
export -f aio_heartbeat aio_claim_file aio_claim_dir aio_safe_edit aio_cleanup

echo "Claude AI Orchestrator integration loaded"
