#!/bin/bash
# Shut down the Jarvis voice orchestrator service.
# Bound to Super+Shift+Q via GNOME custom keybinding.
systemctl --user stop voice-orchestrator
notify-send "Jarvis" "Voice orchestrator stopped."
