#!/usr/bin/env bash
# Amp Integration Hook

export PATH="$HOME/.ai-orchestrator/bin:$PATH"
export AIO_TOOL="amp"

_aio_ensure_registered() {
    if [[ ! -f "$HOME/.ai-orchestrator/.current_instance" ]] || \
       ! grep -q "^amp-" "$HOME/.ai-orchestrator/.current_instance" 2>/dev/null; then
        aio register amp "$(pwd)"
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

echo "Amp AI Orchestrator integration loaded"
