#!/bin/bash
# Start the Jarvis voice orchestrator service.
# Bound to Super+Shift+A via GNOME custom keybinding.
systemctl --user start voice-orchestrator
notify-send "Jarvis" "Voice orchestrator started."
