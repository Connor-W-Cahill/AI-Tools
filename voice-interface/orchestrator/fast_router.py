"""
Fast local command router — handles simple commands without calling Codex.

Matches patterns like:
  "tell window 2 to fix the tests"
  "send window 1 refactor the auth module"
  "check window 3" / "check on window 3" / "status of window 3"
  "switch to window 2"
  "cancel window 1"
  "list windows"
  "what's everyone doing" / "status"

Returns (action, response_text) or None if the command needs Codex.
"""

import re
import subprocess
from typing import Optional, Tuple

from task_router import TaskRouter


class FastRouter:
    def __init__(self, task_router: TaskRouter):
        self.task_router = task_router

    def try_route(self, text: str) -> Optional[Tuple[str, str]]:
        """Try to handle the command locally. Returns (action, spoken_response) or None."""
        text = text.lower().strip()

        # ── "tell/send/ask window N to ..." ─────────────────────────
        m = re.match(
            r'(?:tell|send|ask|have|get)\s+(?:window\s+)?(\d+)\s+(?:to\s+)?(.*)',
            text
        )
        if m:
            window = int(m.group(1))
            prompt = m.group(2).strip()
            if prompt:
                ok = self.task_router.assign_task(window, prompt)
                if ok:
                    return ("assign", f"Sent to window {window}.")
                else:
                    return ("error", f"Couldn't reach window {window}.")

        # ── "tell/send claude/gemini/codex to ..." (by name) ────────
        m = re.match(
            r'(?:tell|send|ask|have|get)\s+(claude|gemini|codex|opencode)\s+(?:to\s+)?(.*)',
            text
        )
        if m:
            name = m.group(1)
            prompt = m.group(2).strip()
            if prompt:
                window = self._find_window_by_name(name)
                if window is not None:
                    ok = self.task_router.assign_task(window, prompt)
                    if ok:
                        return ("assign", f"Sent to {name} in window {window}.")
                    else:
                        return ("error", f"Couldn't reach {name}'s window.")
                else:
                    return ("error", f"I can't find a window named {name}.")

        # ── "check/status window N" ─────────────────────────────────
        m = re.match(
            r'(?:check|status)\s+(?:on\s+|of\s+)?(?:window\s+)?(\d+)',
            text
        )
        if m:
            window = int(m.group(1))
            snippet = self._capture_pane(window)
            if snippet:
                # Trim to last few meaningful lines
                lines = [l for l in snippet.strip().splitlines() if l.strip()]
                summary = " ".join(lines[-3:])[:200]
                return ("status", f"Window {window}: {summary}")
            else:
                return ("error", f"Couldn't read window {window}.")

        # ── "switch to window N" ────────────────────────────────────
        m = re.match(r'(?:switch|go)\s+(?:to\s+)?(?:window\s+)?(\d+)', text)
        if m:
            window = int(m.group(1))
            self.task_router.switch_window(window)
            return ("switch", f"Switched to window {window}.")

        # ── "cancel window N" ──────────────────────────────────────
        m = re.match(r'(?:cancel|stop|kill)\s+(?:window\s+)?(\d+)', text)
        if m:
            window = int(m.group(1))
            self.task_router.cancel_task(window)
            return ("cancel", f"Cancelled window {window}.")

        # ── "list windows" ─────────────────────────────────────────
        if re.match(r'(?:list|show)\s+(?:all\s+)?windows', text):
            windows = self.task_router.list_windows()
            if windows:
                names = [f"window {w['window']} {w['name']}" for w in windows]
                return ("list", f"You have {len(windows)} windows: {', '.join(names)}.")
            return ("list", "No tmux windows found.")

        # Not a simple command — needs Codex
        return None

    def _find_window_by_name(self, name: str) -> Optional[int]:
        """Find a tmux window index by name substring."""
        try:
            r = subprocess.run(
                ["tmux", "list-windows", "-F", "#{window_index} #{window_name}"],
                capture_output=True, text=True, timeout=3
            )
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    parts = line.split(None, 1)
                    if len(parts) == 2 and name.lower() in parts[1].lower():
                        return int(parts[0])
        except Exception:
            pass
        return None

    def _capture_pane(self, window: int) -> Optional[str]:
        """Capture recent output from a tmux pane."""
        try:
            r = subprocess.run(
                ["tmux", "capture-pane", "-t", str(window), "-p", "-S", "-10"],
                capture_output=True, text=True, timeout=3
            )
            if r.returncode == 0:
                return r.stdout
        except Exception:
            pass
        return None
