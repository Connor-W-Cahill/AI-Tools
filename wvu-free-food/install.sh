#!/usr/bin/env bash
# Install wvu-food systemd user timer
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "Installing WVU Free Food scraper..."

# Create .env if missing
if [[ ! -f "$SCRIPT_DIR/.env" ]]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo ""
    echo "  ⚠  Created .env from .env.example"
    echo "  Edit $SCRIPT_DIR/.env and add your WVU credentials before running."
    echo ""
fi

# Symlink systemd units
mkdir -p "$SYSTEMD_USER_DIR"
ln -sf "$SCRIPT_DIR/wvu-food.service" "$SYSTEMD_USER_DIR/wvu-food.service"
ln -sf "$SCRIPT_DIR/wvu-food.timer"   "$SYSTEMD_USER_DIR/wvu-food.timer"

systemctl --user daemon-reload
systemctl --user enable --now wvu-food.timer

echo "Timer installed. Next run:"
systemctl --user list-timers wvu-food.timer --no-pager
