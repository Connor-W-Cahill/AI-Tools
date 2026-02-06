"""
Codex CLI brain for the orchestrator.

Uses `codex exec` in non-interactive mode to process voice commands.
Codex has full shell access, so it can run tmux commands, beads, etc. directly.
No external API key needed — uses Codex's own auth.

Features:
- Conversation memory (rolling history within a session)
- Screen awareness (window list + GPT-4o vision)
- Keyboard/mouse control via xdotool
"""

import os
import subprocess
import tempfile
import time
from typing import List, Optional

from screen import get_screen_context, get_screen_context_with_vision


SYSTEM_CONTEXT = """You are Jarvis, a voice AI orchestrator managing multiple AI assistant instances in tmux windows.
The user is speaking to you via voice. Your response will be read aloud via text-to-speech.

RULES:
- Keep responses SHORT and conversational (1-3 sentences max)
- No markdown, code blocks, bullet points, or formatting — plain spoken English only
- You have full shell access. Use tmux commands to manage windows.
- To send a prompt to a window: tmux set-buffer "text" && tmux paste-buffer -t WINDOW && tmux send-keys -t WINDOW Enter
- To check a window: tmux capture-pane -t WINDOW -p -S -30
- To list windows: tmux list-windows
- To switch window: tmux select-window -t WINDOW
- To cancel: tmux send-keys -t WINDOW C-c
- For task tracking use the `bd` command (e.g. bd ready, bd list --status=open, bd create, bd close)

SCREEN & DESKTOP CONTROL:
- You can see the user's screen — open windows and active app are provided in context
- You can take a screenshot: scrot /tmp/screen.png
- You can OCR it: tesseract /tmp/screen.png stdout
- KEYBOARD CONTROL: xdotool type --delay 50 "text to type"
- KEYBOARD SHORTCUTS: xdotool key ctrl+a, xdotool key Return, xdotool key Tab
- MOUSE MOVE: xdotool mousemove X Y
- MOUSE CLICK: xdotool click 1 (left), xdotool click 3 (right)
- MOUSE MOVE+CLICK: xdotool mousemove X Y click 1
- FOCUS WINDOW: xdotool search --name "Firefox" windowactivate
- SCROLL: xdotool click 4 (up) or click 5 (down)
- GET MOUSE POSITION: xdotool getmouselocation
- GET ACTIVE WINDOW: xdotool getactivewindow getwindowname
- IMPORTANT: When using xdotool to type or click, make sure the right window is focused first
- You can combine: xdotool search --name "Firefox" windowactivate --sync && xdotool type "hello"

CONVERSATION:
- You have memory of previous exchanges in this conversation (shown below)
- Reference earlier context naturally — the user doesn't need to repeat themselves
- When the user says to assign work, send the prompt to the appropriate tmux window
- When checking status, read the pane output and summarize what's happening
- NEVER include shell commands in your spoken response — just tell the user what you did or found"""

# Max conversation turns to keep in memory
MAX_HISTORY = 10


class Brain:
    def __init__(self, task_router=None, pane_monitor=None):
        self.task_router = task_router
        self.pane_monitor = pane_monitor
        self.history: List[dict] = []

    def think(self, user_text: str) -> str:
        """Send user message to Codex and get a response."""
        # Always include basic screen context
        screen_ctx = get_screen_context()

        # If user is asking about their screen, include vision analysis
        screen_keywords = ["screen", "see", "looking at", "open", "running", "browser",
                           "window", "app", "application", "tab", "showing", "display",
                           "what's on", "what is on", "desktop", "fill", "form", "click",
                           "type", "mouse", "cursor"]
        needs_vision = any(kw in user_text.lower() for kw in screen_keywords)
        if needs_vision:
            screen_ctx = get_screen_context_with_vision(user_text)

        # Build conversation history string
        history_str = ""
        if self.history:
            history_str = "\nCONVERSATION HISTORY:\n"
            for entry in self.history[-MAX_HISTORY:]:
                history_str += f"User: {entry['user']}\nJarvis: {entry['response']}\n"

        prompt = (
            f"{SYSTEM_CONTEXT}\n\n"
            f"CURRENT SCREEN STATE:\n{screen_ctx}\n"
            f"{history_str}\n"
            f"The user said: \"{user_text}\"\n\n"
            f"Do what they asked (run commands if needed), then respond with a SHORT spoken sentence."
        )

        # Write response to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            output_file = f.name

        try:
            result = subprocess.run(
                [
                    "codex", "exec",
                    "--dangerously-bypass-approvals-and-sandbox",
                    "--skip-git-repo-check",
                    "-o", output_file,
                    prompt
                ],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.path.expanduser("~")
            )

            print(f"[Brain] Codex exit code: {result.returncode}", flush=True)
            if result.stderr:
                print(f"[Brain] Codex stderr: {result.stderr[:200]}", flush=True)

            try:
                with open(output_file, 'r') as f:
                    response = f.read().strip()
            except Exception:
                response = ""

            if not response:
                response = result.stdout.strip()
                lines = response.splitlines()
                spoken = [l for l in lines if l.strip() and not l.startswith('$') and not l.startswith('+')]
                response = " ".join(spoken[-3:]) if spoken else "I ran into an issue processing that."

            # Clean up formatting
            response = response.replace('```', '').replace('**', '').replace('`', '')
            response = response.replace('#', '').strip()

            if len(response) > 500:
                response = response[:500].rsplit('.', 1)[0] + '.'

            # Save to conversation memory
            self.history.append({"user": user_text, "response": response})

            return response

        except subprocess.TimeoutExpired:
            return "That took too long. Could you try a simpler request?"
        except Exception as e:
            print(f"[Brain] Error: {e}", flush=True)
            return "I had trouble processing that."
        finally:
            try:
                os.unlink(output_file)
            except OSError:
                pass

    def reset(self):
        """Clear conversation memory."""
        self.history.clear()
