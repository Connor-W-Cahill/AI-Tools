"""
Tmux pane monitor - detects when AI instances are working, idle, or errored.

Uses `tmux capture-pane` to periodically read pane contents and detect state changes.
Fires callbacks when an AI transitions between states.
"""

import subprocess
import threading
import time
import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


class PaneState(Enum):
    UNKNOWN = "unknown"
    WORKING = "working"    # AI is actively producing output
    IDLE = "idle"          # Prompt returned, waiting for input
    ERRORED = "errored"    # Error detected in output


@dataclass
class PaneInfo:
    window: int
    state: PaneState = PaneState.UNKNOWN
    last_output: str = ""
    last_change: float = field(default_factory=time.time)
    output_hash: int = 0  # track if output changed between polls


# Patterns that indicate an AI/shell is idle and waiting for input
IDLE_PATTERNS = [
    r"^❯\s*$",                    # Claude Code prompt
    r"^>\s*$",                     # Generic prompt
    r"^\$\s*$",                    # Shell prompt
    r"^connor@.*[\$#]\s*$",        # User shell prompt
    r"^%\s*$",                     # zsh prompt
    r"^\(.*\)\s*❯\s*$",           # Claude Code with context
    r"^\(.*\)\s*>\s*$",           # Prompt with context
]

# Patterns that indicate an error occurred — must be strict to avoid false positives
# Only matches lines that START with error indicators (not just containing the word "error")
ERROR_PATTERNS = [
    r"(?i)^error[:\s]",
    r"(?i)^Traceback \(most recent",
    r"(?i)^.*Exception:",
    r"(?i)^fatal:",
    r"(?i)^FAILED",
    r"(?i)^panic:",
]

IDLE_RE = [re.compile(p) for p in IDLE_PATTERNS]
ERROR_RE = [re.compile(p) for p in ERROR_PATTERNS]


def capture_pane(window: int, lines: int = 30) -> Optional[str]:
    """Capture the last N lines from a tmux pane."""
    try:
        r = subprocess.run(
            ["tmux", "capture-pane", "-t", str(window), "-p", "-S", f"-{lines}"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0:
            return r.stdout
    except (subprocess.TimeoutExpired, Exception):
        pass
    return None


def detect_state(output: str) -> PaneState:
    """Analyze pane output to determine state."""
    if not output:
        return PaneState.UNKNOWN

    lines = output.strip().splitlines()
    if not lines:
        return PaneState.UNKNOWN

    # Check the last few non-empty lines for idle prompt
    tail = [l.strip() for l in lines[-5:] if l.strip()]
    if tail:
        last_line = tail[-1]
        for pat in IDLE_RE:
            if pat.search(last_line):
                return PaneState.IDLE

    # Check recent output for errors
    recent = "\n".join(lines[-15:])
    for pat in ERROR_RE:
        if pat.search(recent):
            return PaneState.ERRORED

    return PaneState.WORKING


class PaneMonitor:
    def __init__(self, poll_interval: float = 2.5):
        self.poll_interval = poll_interval
        self.panes: Dict[int, PaneInfo] = {}
        self._callbacks: List[Callable[[int, PaneState, PaneState, str], None]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def watch(self, window: int):
        """Start monitoring a tmux window. Takes a baseline snapshot to avoid false alerts."""
        if window not in self.panes:
            info = PaneInfo(window=window)
            # Capture initial state as baseline — don't alert on pre-existing content
            output = capture_pane(window)
            if output:
                info.output_hash = hash(output)
                info.last_output = output
                info.state = detect_state(output)
            self.panes[window] = info

    def unwatch(self, window: int):
        """Stop monitoring a tmux window."""
        self.panes.pop(window, None)

    def on_state_change(self, callback: Callable[[int, PaneState, PaneState, str], None]):
        """Register callback: fn(window, old_state, new_state, output_snippet)"""
        self._callbacks.append(callback)

    def get_state(self, window: int) -> PaneState:
        """Get current state of a monitored window."""
        info = self.panes.get(window)
        return info.state if info else PaneState.UNKNOWN

    def get_output(self, window: int, lines: int = 30) -> str:
        """Get current pane output."""
        return capture_pane(window, lines) or ""

    def _poll(self):
        while self._running:
            for window, info in list(self.panes.items()):
                output = capture_pane(window)
                if output is None:
                    continue

                new_hash = hash(output)
                if new_hash == info.output_hash:
                    # Output hasn't changed — if was WORKING, might be stalled/idle
                    if info.state == PaneState.WORKING:
                        # If output hasn't changed for 2 poll cycles, re-check state
                        if time.time() - info.last_change > self.poll_interval * 2:
                            new_state = detect_state(output)
                            if new_state != info.state:
                                old_state = info.state
                                info.state = new_state
                                info.last_change = time.time()
                                self._fire(window, old_state, new_state, output)
                    continue

                info.output_hash = new_hash
                info.last_output = output
                new_state = detect_state(output)

                if new_state != info.state:
                    old_state = info.state
                    info.state = new_state
                    info.last_change = time.time()
                    self._fire(window, old_state, new_state, output)

            time.sleep(self.poll_interval)

    def _fire(self, window: int, old: PaneState, new: PaneState, output: str):
        snippet = "\n".join(output.strip().splitlines()[-5:])
        for cb in self._callbacks:
            try:
                cb(window, old, new, snippet)
            except Exception as e:
                print(f"[PaneMonitor] callback error: {e}", flush=True)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def list_windows(self) -> List[Dict]:
        """List all tmux windows with their monitored state."""
        try:
            r = subprocess.run(
                ["tmux", "list-windows", "-F", "#{window_index} #{window_name}"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode != 0:
                return []
            windows = []
            for line in r.stdout.strip().splitlines():
                parts = line.split(None, 1)
                if parts:
                    idx = int(parts[0])
                    name = parts[1] if len(parts) > 1 else ""
                    state = self.get_state(idx)
                    windows.append({"window": idx, "name": name, "state": state.value})
            return windows
        except Exception:
            return []
