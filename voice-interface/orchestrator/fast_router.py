"""
Fast local command router — handles common commands without calling Claude.

Patterns handled locally (no LLM needed):
  Window management:
    "tell/send window 2 to fix the tests"
    "send claude to refactor auth"
    "check window 3" / "how's window 2 doing" / "what's window 1 up to"
    "switch to window 2"
    "cancel window 1"
    "list windows"
    "what's everyone doing" / "global status"

  Memory:
    "remember that I prefer window 2 for Claude"
    "forget [keyword]"

  Task tracking shortcuts:
    "what tasks are ready" / "bd ready"
    "show my tasks" / "list open tasks"

  Utilities:
    "what time is it" / "what's the date"

Returns (action, response_text) or None if the command needs Claude.
"""

import re
import subprocess
import time
from typing import Optional, Tuple


class FastRouter:
    def __init__(self, task_router, memory=None):
        self.task_router = task_router
        self.memory = memory  # JarvisMemory instance, optional

    def try_route(self, text: str) -> Optional[Tuple[str, str]]:
        """Try to handle the command locally. Returns (action, spoken_response) or None."""
        t = text.lower().strip()

        # ── "tell/send/ask window N to ..." ────────────────────────
        m = re.match(
            r'(?:tell|send|ask|have|get)\s+(?:window\s+)?(\d+)\s+(?:to\s+)?(.*)',
            t
        )
        if m:
            window = int(m.group(1))
            prompt = m.group(2).strip()
            if prompt:
                ok = self.task_router.assign_task(window, prompt)
                if ok:
                    return ("assign", "Sent to window {}.".format(window))
                return ("error", "Couldn't reach window {}.".format(window))

        # ── "tell/send claude/gemini/codex to ..." (by name) ───────
        m = re.match(
            r'(?:tell|send|ask|have|get)\s+(claude|gemini|codex|opencode|qwen)\s+(?:to\s+)?(.*)',
            t
        )
        if m:
            name = m.group(1)
            prompt = m.group(2).strip()
            if prompt:
                window = self._find_window_by_name(name)
                if window is not None:
                    ok = self.task_router.assign_task(window, prompt)
                    if ok:
                        return ("assign", "Sent to {} in window {}.".format(name, window))
                    return ("error", "Couldn't reach {}'s window.".format(name))
                return ("error", "I can't find a window named {}.".format(name))

        # ── Check/status window N (many phrasings) ─────────────────
        m = re.match(
            r'(?:check|status|how\'?s?|what\'?s?|what is)\s+'
            r'(?:on\s+|of\s+|window\s+)?(\d+)'
            r'(?:\s+(?:up to|doing|running|working on|saying))?',
            t
        )
        if m:
            window = int(m.group(1))
            snippet = self._capture_pane(window)
            if snippet:
                lines = [l for l in snippet.strip().splitlines() if l.strip()]
                summary = " ".join(lines[-3:])[:200]
                return ("status", "Window {}: {}".format(window, summary))
            return ("error", "Couldn't read window {}.".format(window))

        # ── "how's/what's <name> doing" ─────────────────────────────
        m = re.match(
            r'(?:how\'?s?|what\'?s?|what is)\s+'
            r'(claude|gemini|codex|opencode|qwen)\s*'
            r'(?:doing|up to|running|working on)?',
            t
        )
        if m:
            name = m.group(1)
            window = self._find_window_by_name(name)
            if window is not None:
                snippet = self._capture_pane(window)
                if snippet:
                    lines = [l for l in snippet.strip().splitlines() if l.strip()]
                    summary = " ".join(lines[-3:])[:200]
                    return ("status", "{} in window {}: {}".format(name, window, summary))
                return ("error", "Couldn't read {}'s window.".format(name))
            return ("error", "No window found for {}.".format(name))

        # ── "what's everyone doing" / global status ─────────────────
        if re.match(
            r'(?:what(?:\'s?|\s+is|\s+are)?\s+(?:everyone|all\s+(?:the\s+)?windows?|going on|happening)|'
            r'global\s+status|all\s+windows?|status\s+all)',
            t
        ):
            return ("global_status", self._global_status())

        # ── Switch to window N ──────────────────────────────────────
        m = re.match(r'(?:switch|go|jump)\s+(?:to\s+)?(?:window\s+)?(\d+)', t)
        if m:
            window = int(m.group(1))
            self.task_router.switch_window(window)
            return ("switch", "Switched to window {}.".format(window))

        # ── Cancel window N ─────────────────────────────────────────
        m = re.match(r'(?:cancel|stop|kill|abort)\s+(?:window\s+)?(\d+)', t)
        if m:
            window = int(m.group(1))
            self.task_router.cancel_task(window)
            return ("cancel", "Cancelled window {}.".format(window))

        # ── List windows ────────────────────────────────────────────
        if re.match(r'(?:list|show)\s+(?:all\s+)?windows?', t):
            windows = self.task_router.list_windows()
            if windows:
                names = ["window {} {}".format(w["window"], w["name"]) for w in windows]
                return ("list", "You have {} windows: {}.".format(len(windows), ", ".join(names)))
            return ("list", "No tmux windows found.")

        # ── Memory: remember fact ────────────────────────────────────
        m = re.match(r'(?:remember|note|save|store)\s+(?:that\s+)?(.*)', t)
        if m:
            fact = m.group(1).strip()
            if fact and self.memory:
                self.memory.add_fact(fact)
                return ("remember", "Got it, I'll remember that.")
            return ("remember", "What would you like me to remember?")

        # ── Memory: forget ───────────────────────────────────────────
        m = re.match(r'(?:forget|remove|delete)\s+(?:that\s+)?(.*)', t)
        if m:
            keyword = m.group(1).strip()
            if keyword and self.memory:
                removed = self.memory.remove_fact(keyword)
                if removed:
                    return ("forget", "Removed {} fact{}.".format(
                        removed, "s" if removed > 1 else ""))
                return ("forget", "No facts matched that.")
            return ("forget", "What should I forget?")

        # ── Task tracking shortcuts ──────────────────────────────────
        if re.match(r'(?:what\'?s?\s+ready|show\s+(?:ready\s+)?tasks?|bd\s+ready|beads\s+ready)', t):
            out = self._run("bd ready")
            if out and out != "(no output)":
                lines = [l for l in out.strip().splitlines() if l.strip()]
                if lines:
                    return ("tasks", "Ready tasks: {}.".format("; ".join(lines[:3])))
            return ("tasks", "No tasks ready right now.")

        if re.match(r'(?:list|show)\s+(?:open\s+|my\s+)?tasks?', t):
            out = self._run("bd list --status=open")
            if out and out != "(no output)":
                lines = [l for l in out.strip().splitlines() if l.strip()][:5]
                return ("tasks", "Open tasks: {}.".format("; ".join(lines)))
            return ("tasks", "No open tasks found.")

        # ── Time / date ──────────────────────────────────────────────
        if re.match(r'what\'?s?\s+(?:the\s+)?time', t):
            return ("time", "It's {}.".format(time.strftime("%I:%M %p").lstrip("0")))

        if re.match(r'what\'?s?\s+(?:the\s+)?(?:date|today)', t):
            return ("date", "Today is {}.".format(time.strftime("%A, %B %-d")))

        # Not a simple command — let Claude handle it
        return None

    # ── Helpers ─────────────────────────────────────────────────────────

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

    def _run(self, cmd: str) -> str:
        """Run a shell command and return its output."""
        try:
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            out = r.stdout.strip()
            return out if out else r.stderr.strip()
        except Exception:
            return ""

    def _global_status(self) -> str:
        """Summarize all tmux windows' current activity."""
        windows = self.task_router.list_windows()
        if not windows:
            return "No tmux windows are open."

        summaries = []
        for w in windows[:5]:
            idx = w["window"]
            name = w["name"]
            snippet = self._capture_pane(idx)
            if snippet:
                lines = [l for l in snippet.strip().splitlines() if l.strip()]
                last = lines[-1][:60] if lines else "idle"
                summaries.append("window {} {}: {}".format(idx, name, last))
            else:
                summaries.append("window {} {}: no output".format(idx, name))

        return "Status: " + "; ".join(summaries) + "."
