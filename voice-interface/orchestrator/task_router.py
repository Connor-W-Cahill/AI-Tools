"""
Task router - sends commands to specific tmux windows and tracks assignments.

Maintains a registry of what task is assigned to which window.
"""

import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Assignment:
    window: int
    prompt: str
    assigned_at: float = field(default_factory=time.time)
    status: str = "active"  # active, completed, cancelled, errored


class TaskRouter:
    def __init__(self):
        self.assignments: Dict[int, Assignment] = {}

    def assign_task(self, window: int, prompt: str) -> bool:
        """Send a prompt to a tmux window and track it."""
        # Paste via tmux buffer to handle multi-line and special chars
        r1 = subprocess.run(
            ["tmux", "set-buffer", prompt],
            capture_output=True, text=True
        )
        if r1.returncode != 0:
            return False

        r2 = subprocess.run(
            ["tmux", "paste-buffer", "-t", str(window)],
            capture_output=True, text=True
        )
        if r2.returncode != 0:
            return False

        # Send Enter to submit
        time.sleep(0.1)
        r3 = subprocess.run(
            ["tmux", "send-keys", "-t", str(window), "Enter"],
            capture_output=True, text=True
        )
        if r3.returncode != 0:
            return False

        self.assignments[window] = Assignment(window=window, prompt=prompt)
        return True

    def type_to_window(self, window: int, text: str) -> bool:
        """Paste text into a window without submitting (no Enter)."""
        r1 = subprocess.run(
            ["tmux", "set-buffer", text],
            capture_output=True, text=True
        )
        if r1.returncode != 0:
            return False

        r2 = subprocess.run(
            ["tmux", "paste-buffer", "-t", str(window)],
            capture_output=True, text=True
        )
        return r2.returncode == 0

    def cancel_task(self, window: int) -> bool:
        """Send Ctrl+C to cancel current work in a window."""
        r = subprocess.run(
            ["tmux", "send-keys", "-t", str(window), "C-c"],
            capture_output=True, text=True
        )
        if window in self.assignments:
            self.assignments[window].status = "cancelled"
        return r.returncode == 0

    def mark_completed(self, window: int):
        """Mark a window's assignment as completed."""
        if window in self.assignments:
            self.assignments[window].status = "completed"

    def mark_errored(self, window: int):
        """Mark a window's assignment as errored."""
        if window in self.assignments:
            self.assignments[window].status = "errored"

    def get_assignment(self, window: int) -> Optional[Assignment]:
        return self.assignments.get(window)

    def get_active_assignments(self) -> List[Assignment]:
        return [a for a in self.assignments.values() if a.status == "active"]

    def get_all_assignments(self) -> Dict[int, dict]:
        result = {}
        for w, a in self.assignments.items():
            result[w] = {
                "window": a.window,
                "prompt": a.prompt[:100] + ("..." if len(a.prompt) > 100 else ""),
                "status": a.status,
                "assigned_at": a.assigned_at,
                "elapsed": round(time.time() - a.assigned_at),
            }
        return result

    def switch_window(self, window: int) -> bool:
        """Switch tmux focus to a specific window."""
        r = subprocess.run(
            ["tmux", "select-window", "-t", str(window)],
            capture_output=True, text=True
        )
        return r.returncode == 0

    def list_windows(self) -> List[dict]:
        """List all available tmux windows."""
        try:
            r = subprocess.run(
                ["tmux", "list-windows", "-F", "#{window_index} #{window_name} #{window_active}"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode != 0:
                return []
            windows = []
            for line in r.stdout.strip().splitlines():
                parts = line.split(None, 2)
                if parts:
                    idx = int(parts[0])
                    name = parts[1] if len(parts) > 1 else ""
                    active = parts[2] == "1" if len(parts) > 2 else False
                    assignment = self.get_assignment(idx)
                    windows.append({
                        "window": idx,
                        "name": name,
                        "active": active,
                        "task": assignment.prompt[:60] if assignment else None,
                        "task_status": assignment.status if assignment else None,
                    })
            return windows
        except Exception:
            return []
