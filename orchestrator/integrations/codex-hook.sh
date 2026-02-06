#!/usr/bin/env bash
# Codex Integration Hook
# Add to your Codex instructions or shell profile

export PATH="$HOME/.ai-orchestrator/bin:$PATH"
export AIO_TOOL="codex"

_aio_ensure_registered() {
    if [[ ! -f "$HOME/.ai-orchestrator/.current_instance" ]] || \
       ! grep -q "^codex-" "$HOME/.ai-orchestrator/.current_instance" 2>/dev/null; then
        aio register codex "$(pwd)"
    fi
}

aio_heartbeat() {
    _aio_ensure_registered
    aio heartbeat >/dev/null 2>&1 &
}

aio_claim_file() {
    _aio_ensure_registered
    aio claim file "$1"
}

aio_claim_dir() {
    _aio_ensure_registered
    aio claim directory "$1"
}

aio_safe_edit() {
    local file="$1"
    if aio check "$file" >/dev/null 2>&1; then
        return 0
    else
        echo "WARNING: $file is claimed by another AI instance"
        return 1
    fi
}

aio_cleanup() {
    aio unregister 2>/dev/null || true
}

trap aio_cleanup EXIT
export -f aio_heartbeat aio_claim_file aio_claim_dir aio_safe_edit aio_cleanup

echo "Codex AI Orchestrator integration loaded"
