#!/usr/bin/env bash
#
# setup.sh — Bootstrap AI-Tools environment on a new machine
#
# Usage: ./setup.sh [--voice]
#   --voice   Also install voice-interface systemd services
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VOICE=false

for arg in "$@"; do
    case "$arg" in
        --voice) VOICE=true ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

# --- Colors ---
G=$'\e[32m' Y=$'\e[33m' R=$'\e[31m' B=$'\e[1m' N=$'\e[0m'
info()  { echo "${G}[+]${N} $*"; }
warn()  { echo "${Y}[!]${N} $*"; }
err()   { echo "${R}[x]${N} $*" >&2; }
step()  { echo; echo "${B}=== $* ===${N}"; }

# ============================================================
step "1. Orchestrator (aio CLI)"
# ============================================================

AIO_HOME="$HOME/.ai-orchestrator"
mkdir -p "$AIO_HOME"/{bin,integrations,claims,context,instances,logs,tool-instructions}

# Symlink binaries
for f in "$REPO_DIR"/orchestrator/bin/*; do
    target="$AIO_HOME/bin/$(basename "$f")"
    ln -sf "$f" "$target"
    info "Linked $(basename "$f") → $target"
done

# Symlink integrations
for f in "$REPO_DIR"/orchestrator/integrations/*; do
    target="$AIO_HOME/integrations/$(basename "$f")"
    ln -sf "$f" "$target"
    info "Linked $(basename "$f") → $target"
done

# Copy schema + docs (not symlinked — aio may modify state.json in-place)
for f in schema.json INSTRUCTIONS.md PLAYBOOK.md CONTEXT.md update-context.sh; do
    if [[ -f "$REPO_DIR/orchestrator/$f" ]]; then
        cp -n "$REPO_DIR/orchestrator/$f" "$AIO_HOME/$f" 2>/dev/null || true
    fi
done

# Initialize state.json if missing
if [[ ! -f "$AIO_HOME/state.json" ]]; then
    echo '{"instances":{},"claims":{},"context":[]}' > "$AIO_HOME/state.json"
    info "Created empty state.json"
fi

# ============================================================
step "2. Hub (ai CLI)"
# ============================================================

mkdir -p "$HOME/.local/bin"
ln -sf "$REPO_DIR/hub/ai" "$HOME/.local/bin/ai"
info "Linked ai → $HOME/.local/bin/ai"

# Bash completion
COMP_DIR="$HOME/.local/share/bash-completion/completions"
mkdir -p "$COMP_DIR"
ln -sf "$REPO_DIR/hub/completions/ai" "$COMP_DIR/ai"
info "Linked ai completion → $COMP_DIR/ai"

# Check PATH
if ! echo "$PATH" | tr ':' '\n' | grep -q "$HOME/.local/bin"; then
    warn "\$HOME/.local/bin not in PATH — add to your shell rc"
fi

# ============================================================
step "3. MCP Servers"
# ============================================================

for server in whisper-voice task-state; do
    srv_dir="$REPO_DIR/mcp-servers/$server"
    if [[ -f "$srv_dir/requirements.txt" ]]; then
        if command -v pip3 &>/dev/null; then
            info "Installing $server Python dependencies..."
            pip3 install --user -q -r "$srv_dir/requirements.txt" || warn "pip install failed for $server"
        else
            warn "pip3 not found — install $server deps manually: pip3 install -r $srv_dir/requirements.txt"
        fi
    fi
done

# Symlink MCP servers into ~/.claude/mcp-servers/ for Claude to discover
MCP_HOME="$HOME/.claude/mcp-servers"
mkdir -p "$MCP_HOME"
for server in whisper-voice task-state; do
    target="$MCP_HOME/$server"
    if [[ ! -e "$target" ]]; then
        ln -sf "$REPO_DIR/mcp-servers/$server" "$target"
        info "Linked $server → $target"
    else
        warn "$target already exists — skipping (remove manually to re-link)"
    fi
done

# ============================================================
step "4. Agent Definitions"
# ============================================================

# Symlink agents into locations AI tools expect
for tool_dir in .codex/agents .opencode/agents; do
    full="$REPO_DIR/$tool_dir"
    mkdir -p "$(dirname "$full")"
    if [[ ! -e "$full" ]]; then
        ln -sf "$REPO_DIR/agents" "$full"
        info "Linked agents → $full"
    fi
done

# ============================================================
step "5. Config Templates"
# ============================================================

# OpenCode config
OC_DIR="$REPO_DIR/.opencode"
mkdir -p "$OC_DIR"
for f in claude-settings.json claude-settings.local.json; do
    src="$REPO_DIR/config/opencode/$f"
    target="$OC_DIR/$f"
    if [[ -f "$src" ]] && [[ ! -f "$target" ]]; then
        cp "$src" "$target"
        info "Copied $f → $OC_DIR/"
    fi
done

# Ralph config
if [[ -f "$REPO_DIR/config/ralph.yml" ]] && [[ ! -f "$REPO_DIR/ralph.yml" ]]; then
    ln -sf "$REPO_DIR/config/ralph.yml" "$REPO_DIR/ralph.yml"
    info "Linked ralph.yml"
fi

# ============================================================
step "6. Beads (bd) — Task Tracker"
# ============================================================

if command -v bd &>/dev/null; then
    info "bd found: $(command -v bd)"
else
    warn "bd not installed. Install it:"
    echo "  curl -fsSL https://github.com/beads-project/beads/releases/latest/download/bd-linux-amd64 -o ~/.local/bin/bd"
    echo "  chmod +x ~/.local/bin/bd"
fi

# ============================================================
# Voice interface (optional)
# ============================================================

if $VOICE; then
    step "7. Voice Interface (Jarvis)"
    VI_DIR="$REPO_DIR/voice-interface"
    if [[ -d "$VI_DIR" ]]; then
        if [[ -f "$VI_DIR/orchestrator/requirements.txt" ]]; then
            info "Installing voice-interface Python dependencies..."
            pip3 install --user -q -r "$VI_DIR/orchestrator/requirements.txt" || warn "pip install failed"
        fi
        # Install systemd user services
        SYSTEMD_DIR="$HOME/.config/systemd/user"
        mkdir -p "$SYSTEMD_DIR"
        for svc in "$VI_DIR"/*.service; do
            [[ -f "$svc" ]] || continue
            cp "$svc" "$SYSTEMD_DIR/"
            info "Installed $(basename "$svc")"
        done
        systemctl --user daemon-reload
        info "Run: systemctl --user enable --now voice-orchestrator.service"
    else
        warn "voice-interface/ not found"
    fi
fi

# ============================================================
step "Done"
# ============================================================

info "AI-Tools environment is set up."
echo
echo "  ai ?      — Quick help"
echo "  ai s      — Status dashboard"
echo "  bd ready  — Available tasks"
echo
if ! $VOICE; then
    echo "  Re-run with --voice to install voice interface services."
fi
