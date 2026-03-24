"""
Claude brain for the Jarvis orchestrator.

Primary path: Anthropic SDK with adaptive thinking (claude-opus-4-6).
Secondary: Claude Code CLI (`claude -p`) — uses Claude Pro subscription.
Tertiary: LiteLLM proxy (claude-haiku/claude-sonnet) if CLI unavailable.
Final fallback: Ollama qwen2.5:3b for simple/knowledge queries.

Features:
  - Streaming responses -> sentence-by-sentence TTS
  - Tool use: run_shell, read_pane
  - Adaptive thinking for complex queries (claude-opus-4-6)
  - Persistent memory across sessions (JarvisMemory)
  - Conversation history within a session

Uses the requests library for raw HTTP calls to avoid openai SDK version issues.
"""
import json
import os
import re
import subprocess
import sys
import time
from typing import Generator, Iterator, List, Optional

import requests
try:
    import anthropic as _anthropic_lib
    _ANTHROPIC_SDK_AVAILABLE = True
except ImportError:
    _ANTHROPIC_SDK_AVAILABLE = False

from screen import get_screen_context, get_screen_context_with_vision
from local_llm import classify_intent, quick_answer, _ollama_available
from memory import JarvisMemory

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'rag'))
try:
    from knowledge_base import KnowledgeBase
    _kb = KnowledgeBase()
except Exception:
    _kb = None

# ── Config ──────────────────────────────────────────────────────────────

LITELLM_URL = "http://localhost:4000"
QUICK_MODEL = "claude-haiku"
FULL_MODEL = "claude-sonnet"
MAX_HISTORY = 10
MAX_TOOL_ROUNDS = 3

HUB_BRIEF_PATH = "/home/connor/AI-Tools/hub/context/current.md"
HUB_BRIEF_SCRIPT = "/home/connor/AI-Tools/hub/scripts/generate-brief.sh"
HUB_BRIEF_MAX_CHARS = 4000

SYSTEM_BASE = """You are Jarvis, a voice AI assistant in a developer's workspace.
Responses will be read aloud via text-to-speech.

RESPONSE RULES:
- SHORT and conversational (1-3 sentences max)
- No markdown, bullet points, code blocks, asterisks, or special characters
- Plain spoken English only
- When running commands: report what you did or found, not the command itself

TOOLS AVAILABLE:
- run_shell: execute any shell command (tmux, bd, git, xdotool, file ops, etc.)
- read_pane: quickly read recent output from a tmux window

TMUX WINDOW MANAGEMENT:
- List: tmux list-windows -F '#{window_index} #{window_name}'
- Send task: tmux set-buffer "text" && tmux paste-buffer -t N && tmux send-keys -t N Enter
- Read output: tmux capture-pane -t N -p -S -30
- Switch to: tmux select-window -t N
- Cancel: tmux send-keys -t N C-c

TASK TRACKING (beads):
- bd ready          -> show tasks ready to work on
- bd list --status=open  -> all open tasks
- bd create --title="..." --type=task --priority=2
- bd close <id>     -> mark complete
- bd show <id>      -> task details

DESKTOP CONTROL:
- xdotool type --delay 50 "text"
- xdotool key ctrl+c
- xdotool mousemove X Y click 1
- xdotool search --name "App" windowactivate"""

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": (
                "Execute a shell command and return its output. "
                "Use for: tmux window management, bd task tracking, "
                "xdotool desktop control, git, file operations, system info."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute."
                    }
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_pane",
            "description": "Read recent output from a tmux window without sending anything.",
            "parameters": {
                "type": "object",
                "properties": {
                    "window": {
                        "type": "integer",
                        "description": "tmux window index number"
                    },
                    "lines": {
                        "type": "integer",
                        "description": "Number of recent lines to read (default 20)",
                        "default": 20
                    }
                },
                "required": ["window"]
            }
        }
    }
]

# ── Anthropic API key loader ─────────────────────────────────────────────

_LITELLM_ENV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "litellm", "env"
)

def _load_anthropic_key():
    """Return ANTHROPIC_API_KEY from environment or litellm/env file."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    try:
        with open(os.path.abspath(_LITELLM_ENV_PATH)) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


# ── Tool execution ───────────────────────────────────────────────────────

def _run_shell(command):
    """Execute a shell command and return output (stdout + stderr combined)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.expanduser("~"),
            env=os.environ.copy(),
        )
        out = result.stdout.strip()
        err = result.stderr.strip()
        if out and err:
            return "{}\n{}".format(out, err)
        combined = out or err
        return combined if combined else "(no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return "Error: {}".format(e)


def _read_pane(window, lines=20):
    """Read recent output from a tmux pane."""
    try:
        r = subprocess.run(
            ["tmux", "capture-pane", "-t", str(window), "-p", "-S", "-{}".format(lines)],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip() if r.returncode == 0 else "Couldn't read window {}.".format(window)
    except Exception as e:
        return "Error reading pane: {}".format(e)


def _execute_tool(name, arguments):
    """Dispatch a tool call and return its string result."""
    if name == "run_shell":
        cmd = arguments.get("command", "")
        print("[Brain] run_shell: {}".format(cmd[:100]), flush=True)
        return _run_shell(cmd)
    elif name == "read_pane":
        window = arguments.get("window", 0)
        lines = arguments.get("lines", 20)
        print("[Brain] read_pane: window={}".format(window), flush=True)
        return _read_pane(window, lines)
    return "Unknown tool: {}".format(name)


# ── Helpers ─────────────────────────────────────────────────────────────

def _load_hub_brief():
    try:
        if os.path.isfile(HUB_BRIEF_SCRIPT) and os.access(HUB_BRIEF_SCRIPT, os.X_OK):
            subprocess.run([HUB_BRIEF_SCRIPT], timeout=5, check=False, capture_output=True)
        if os.path.isfile(HUB_BRIEF_PATH):
            with open(HUB_BRIEF_PATH) as f:
                data = f.read().strip()
            if data:
                return data[:HUB_BRIEF_MAX_CHARS]
    except Exception:
        pass
    return ""


def _extract_sentences(text):
    """Split text into complete sentences and an incomplete remainder.

    Returns (list_of_sentences, remainder_string).
    Requires >= 8 chars to avoid splitting on short abbreviations.
    """
    sentences = []
    pattern = re.compile(r'([^.!?]+[.!?]+)\s+')
    pos = 0
    for m in pattern.finditer(text):
        s = m.group(1).strip()
        if len(s) >= 8:
            sentences.append(s)
        pos = m.end()
    remainder = text[pos:]
    return sentences, remainder


def _litellm_available():
    """Quick health check for the LiteLLM proxy. Retries once on timeout."""
    for _ in range(2):
        try:
            resp = requests.get("{}/health".format(LITELLM_URL), timeout=4)
            return resp.status_code == 200
        except requests.Timeout:
            continue
        except Exception:
            return False
    return False


def _post_completion(payload, timeout):
    """POST to LiteLLM /chat/completions and return the response object."""
    return requests.post(
        "{}/chat/completions".format(LITELLM_URL),
        json=payload,
        timeout=timeout,
        headers={"Content-Type": "application/json"},
    )


# ── Brain ────────────────────────────────────────────────────────────────

class Brain:
    def __init__(self, task_router=None, pane_monitor=None):
        self.task_router = task_router
        self.pane_monitor = pane_monitor
        self.history: List[dict] = []
        self.memory = JarvisMemory()

        self._litellm_ok = _litellm_available()
        print("[Brain] LiteLLM available: {}".format(self._litellm_ok), flush=True)
        print("[Brain] Session #{}".format(self.memory.session_count), flush=True)

    def _ensure_litellm(self):
        """Re-check availability if previously down."""
        if not self._litellm_ok:
            self._litellm_ok = _litellm_available()
        return self._litellm_ok

    def _build_system(self, screen_ctx=""):
        """Build system prompt with memory and optional screen context."""
        parts = [SYSTEM_BASE]

        mem_str = self.memory.format_for_prompt()
        if mem_str:
            parts.append("\n{}".format(mem_str))

        hub = _load_hub_brief()
        if hub:
            parts.append("\nHUB CONTEXT (source of truth for project state):\n{}".format(hub))

        if screen_ctx:
            parts.append("\nSCREEN STATE:\n{}".format(screen_ctx))

        return "\n".join(parts)

    def _build_messages(self, user_text, mode):
        """Build the messages list for a chat completion request."""
        if mode == "quick":
            screen_ctx = ""
        else:
            screen_ctx = get_screen_context(include_windows=True)
            screen_keywords = ["screen", "see", "window", "app", "browser",
                               "tab", "click", "type", "open", "running", "cursor"]
            if any(kw in user_text.lower() for kw in screen_keywords):
                screen_ctx = get_screen_context_with_vision(user_text)

        system = self._build_system(screen_ctx)

        rag_prefix = ""
        if _kb:
            try:
                results = _kb.search(user_text, n_results=2)
                relevant = [r for r in results if r.get("distance", 999) < 1.5]
                if relevant:
                    rag_ctx = "\n".join("- {}".format(r["document"][:150]) for r in relevant)
                    rag_prefix = "Relevant knowledge:\n{}\n\n".format(rag_ctx)
            except Exception:
                pass

        messages = [{"role": "system", "content": system}]

        for entry in self.history[-MAX_HISTORY:]:
            messages.append({"role": "user", "content": entry["user"]})
            messages.append({"role": "assistant", "content": entry["response"]})

        messages.append({"role": "user", "content": "{}{}".format(rag_prefix, user_text)})
        return messages

    # ── Primary: Anthropic SDK with adaptive thinking ────────────────────

    def _anthropic_sdk_think(self, user_text, mode):
        """Stream using Anthropic SDK directly with adaptive thinking.

        Uses claude-opus-4-6 with thinking: {type: adaptive} for full mode,
        or claude-haiku-4-5 for quick mode.  Yields sentences for TTS, or
        None as a sentinel if the SDK/key is unavailable.
        """
        if not _ANTHROPIC_SDK_AVAILABLE:
            yield None
            return

        api_key = _load_anthropic_key()
        if not api_key:
            print("[Brain] Anthropic API key not found, skipping SDK path.", flush=True)
            yield None
            return

        client = _anthropic_lib.Anthropic(api_key=api_key)

        if mode == "quick":
            model = "claude-haiku-4-5"
            thinking_param = None
            max_tokens = 512
        else:
            model = "claude-opus-4-6"
            thinking_param = {"type": "adaptive"}
            max_tokens = 4096

        system = self._build_system(
            "" if mode == "quick"
            else get_screen_context(include_windows=True)
        )

        messages = []
        for entry in self.history[-MAX_HISTORY:]:
            messages.append({"role": "user", "content": entry["user"]})
            messages.append({"role": "assistant", "content": entry["response"]})

        rag_prefix = ""
        if _kb:
            try:
                results = _kb.search(user_text, n_results=2)
                relevant = [r for r in results if r.get("distance", 999) < 1.5]
                if relevant:
                    rag_ctx = "\n".join("- {}".format(r["document"][:150]) for r in relevant)
                    rag_prefix = "Relevant knowledge:\n{}\n\n".format(rag_ctx)
            except Exception:
                pass

        messages.append({"role": "user", "content": "{}{}".format(rag_prefix, user_text)})

        # Build Anthropic SDK-style tools
        sdk_tools = [
            {
                "name": "run_shell",
                "description": (
                    "Execute a shell command and return its output. "
                    "Use for: tmux, bd task tracking, xdotool desktop control, "
                    "git, file operations, system info."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to run."}
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "read_pane",
                "description": "Read recent output from a tmux window.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "window": {"type": "integer", "description": "tmux window index"},
                        "lines": {"type": "integer", "description": "Lines to read (default 20)"},
                    },
                    "required": ["window"],
                },
            },
        ]

        use_tools = (mode != "quick")
        print("[Brain] Anthropic SDK: model={} thinking={}".format(
            model, thinking_param is not None), flush=True)

        text_buf = ""
        yielded_anything = False

        for _round in range(MAX_TOOL_ROUNDS):
            create_kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages,
            }
            if thinking_param:
                create_kwargs["thinking"] = thinking_param
            if use_tools:
                create_kwargs["tools"] = sdk_tools
                create_kwargs["tool_choice"] = {"type": "auto"}

            try:
                if not use_tools:
                    # True streaming for quick/no-tool path
                    with client.messages.stream(**create_kwargs) as stream:
                        for event in stream:
                            if (event.type == "content_block_delta"
                                    and hasattr(event.delta, "text")):
                                text_buf += event.delta.text
                                sentences, text_buf = _extract_sentences(text_buf)
                                for s in sentences:
                                    yielded_anything = True
                                    yield s
                    if text_buf.strip() and len(text_buf.strip()) >= 8:
                        yielded_anything = True
                        yield text_buf.strip()
                    break

                else:
                    # Non-streaming for reliable tool_use detection
                    response = client.messages.create(**create_kwargs)
                    finish = response.stop_reason

                    if finish != "tool_use":
                        # Collect text and thinking blocks
                        for block in response.content:
                            if block.type == "text":
                                text = block.text.strip()
                                if text:
                                    sentences, remainder = _extract_sentences(text + " ")
                                    for s in sentences:
                                        yielded_anything = True
                                        yield s
                                    if remainder.strip() and len(remainder.strip()) >= 8:
                                        yielded_anything = True
                                        yield remainder.strip()
                        break

                    # Execute tool calls
                    tool_uses = [b for b in response.content if b.type == "tool_use"]
                    if not tool_uses:
                        break

                    # Append assistant turn (include thinking blocks for context)
                    asst_content = []
                    for block in response.content:
                        if block.type == "thinking":
                            asst_content.append({
                                "type": "thinking",
                                "thinking": block.thinking,
                                "signature": block.signature,
                            })
                        elif block.type == "tool_use":
                            asst_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            })
                        elif block.type == "text" and block.text:
                            asst_content.append({"type": "text", "text": block.text})
                    messages.append({"role": "assistant", "content": asst_content})

                    tool_results = []
                    for tu in tool_uses:
                        result_str = _execute_tool(tu.name, tu.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tu.id,
                            "content": result_str[:3000],
                        })
                    messages.append({"role": "user", "content": tool_results})

                    if _round == MAX_TOOL_ROUNDS - 2:
                        messages.append({
                            "role": "user",
                            "content": "Now summarize in 1-2 spoken sentences. No tools.",
                        })
                        use_tools = False

            except _anthropic_lib.AuthenticationError:
                print("[Brain] Anthropic auth error — bad API key.", flush=True)
                yield None
                return
            except _anthropic_lib.RateLimitError:
                print("[Brain] Anthropic rate limit hit.", flush=True)
                yield None
                return
            except Exception as e:
                print("[Brain] Anthropic SDK error: {}".format(e), flush=True)
                yield None
                return

        if not yielded_anything:
            yield None  # sentinel: fall back

    def _clean(self, text):
        """Strip markdown formatting unsuitable for TTS."""
        text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        text = text.replace('**', '').replace('*', '').replace('#', '').strip()
        if len(text) > 500:
            text = text[:500].rsplit('.', 1)[0] + '.'
        return text

    # ── Primary: streaming think ─────────────────────────────────────────

    # ── Primary: Claude Code CLI ─────────────────────────────────────────

    def _claude_code_think(self, user_text, mode):
        """Call `claude -p` as a subprocess to use the Claude Pro subscription.

        Yields sentences as they stream from stdout, or None as final sentinel
        if there was no output (caller should fall back to LiteLLM).
        CLAUDECODE env var is unset to bypass nested session restriction.
        """
        system_parts = [SYSTEM_BASE]
        mem_str = self.memory.format_for_prompt()
        if mem_str:
            system_parts.append(mem_str)
        hub = _load_hub_brief()
        if hub:
            system_parts.append("HUB CONTEXT:\n{}".format(hub))
        if mode == "full":
            screen_ctx = get_screen_context(include_windows=True)
            if screen_ctx:
                system_parts.append("SCREEN STATE:\n{}".format(screen_ctx))

        history_text = ""
        for entry in self.history[-MAX_HISTORY:]:
            history_text += "User: {}\nJarvis: {}\n".format(
                entry["user"], entry["response"]
            )

        full_prompt = "{}\n\n{}User: {}".format(
            "\n\n".join(system_parts), history_text, user_text
        ).strip()

        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE")}

        print("[Brain] Calling claude --print (Claude Pro)...", flush=True)
        try:
            proc = subprocess.Popen(
                ["claude", "--print", full_prompt, "--dangerously-skip-permissions"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=os.path.expanduser("~"),
            )
        except FileNotFoundError:
            print("[Brain] claude CLI not found, falling back.", flush=True)
            return

        text_buf = ""
        yielded_anything = False
        try:
            # claude --print may take 10-30s on first response; stream stdout lines
            for line in proc.stdout:
                text_buf += line
                sentences, text_buf = _extract_sentences(text_buf)
                for s in sentences:
                    s = self._clean(s)
                    if s:
                        yielded_anything = True
                        yield s
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        except Exception as e:
            print("[Brain] claude --print read error: {}".format(e), flush=True)

        if text_buf.strip() and len(text_buf.strip()) >= 8:
            cleaned = self._clean(text_buf.strip())
            if cleaned:
                yielded_anything = True
                yield cleaned

        if not yielded_anything:
            try:
                stderr = proc.stderr.read(300).strip()
            except Exception:
                stderr = ""
            print("[Brain] claude -p no output. stderr: {}".format(stderr), flush=True)
            yield None  # sentinel: fall back to LiteLLM

    def think_streaming(self, user_text, mode="full"):
        """Stream the response as a generator of complete sentences.

        Pipeline:
          1. Anthropic SDK with adaptive thinking (claude-opus-4-6)
          2. Claude Code CLI (Pro subscription)
          3. LiteLLM proxy (claude-sonnet/haiku)
          4. Ollama qwen2.5:3b (local fallback)
        """
        # ── Primary: Anthropic SDK with adaptive thinking ──────────────
        sentences = []
        try:
            for sentence in self._anthropic_sdk_think(user_text, mode):
                if sentence is None:
                    break
                sentences.append(sentence)
                yield self._clean(sentence)

            if sentences:
                self.history.append({"user": user_text, "response": " ".join(sentences)})
                return
        except Exception as e:
            print("[Brain] Anthropic SDK error: {}".format(e), flush=True)

        print("[Brain] Falling back to Claude Code CLI...", flush=True)

        # ── Secondary: Claude Code CLI (uses Claude Pro subscription) ──
        sentences = []
        try:
            for sentence in self._claude_code_think(user_text, mode):
                if sentence is None:
                    # Sentinel: no output, fall through to LiteLLM
                    break
                sentences.append(sentence)
                yield sentence

            if sentences:
                self.history.append({"user": user_text, "response": " ".join(sentences)})
                return
        except Exception as e:
            print("[Brain] Claude Code CLI error: {}".format(e), flush=True)

        print("[Brain] Falling back to LiteLLM...", flush=True)

        # ── Local Ollama fast path ───────────────────────────────────
        if _ollama_available():
            intent = classify_intent(user_text)
            print("[Brain] Local intent: {}".format(intent), flush=True)

            if intent == "simple":
                answer = quick_answer(user_text)
                if answer:
                    self.history.append({"user": user_text, "response": answer})
                    yield answer
                    return

            if intent == "knowledge" and _kb:
                results = _kb.search(user_text, n_results=3)
                if results and results[0].get("distance", 999) < 1.5:
                    ctx = "\n".join(r["document"][:200] for r in results)
                    answer = quick_answer("Context:\n{}\n\nAnswer: {}".format(ctx, user_text))
                    if answer:
                        self.history.append({"user": user_text, "response": answer})
                        yield answer
                        return

        if not self._ensure_litellm():
            fallback = quick_answer(user_text) or "LiteLLM is unavailable right now."
            yield fallback
            return

        model = QUICK_MODEL if mode == "quick" else FULL_MODEL
        timeout = 20 if mode == "quick" else 60
        use_tools = (mode != "quick")

        try:
            messages = self._build_messages(user_text, mode)
            full_response = []

            for sentence in self._stream_sentences(messages, model, timeout, use_tools):
                sentence = self._clean(sentence)
                if sentence:
                    full_response.append(sentence)
                    yield sentence

            combined = " ".join(full_response)
            self.history.append({"user": user_text, "response": combined})

        except Exception as e:
            print("[Brain] Streaming error: {}".format(e), flush=True)
            yield "I had trouble processing that."

    def _stream_sentences(self, messages, model, timeout, use_tools=True):
        """Yield sentences from LiteLLM responses, executing tool calls as needed.

        Strategy:
          - No tools (quick mode): true streaming SSE for minimum first-word latency
          - With tools (full mode): non-streaming to reliably detect tool_calls
            finish_reason, execute tools, then stream the final text response
        """
        msgs = list(messages)

        if not use_tools:
            yield from self._stream_sse(msgs, model, timeout, payload_extra={})
            return

        # ── Agentic tool-use loop (non-streaming for reliable detection) ──
        yielded_anything = False
        for _round in range(MAX_TOOL_ROUNDS):
            payload = {
                "model": model,
                "messages": msgs,
                "stream": False,
                "max_tokens": 400,
                "temperature": 0.3,
                "tools": TOOLS_SCHEMA,
                "tool_choice": "auto",
            }
            try:
                resp = _post_completion(payload, timeout=timeout)
                resp.raise_for_status()
                result = resp.json()
            except requests.ConnectionError:
                self._litellm_ok = False
                yield "I lost connection to my language model."
                return
            except Exception as e:
                print("[Brain] Tool round error: {}".format(e), flush=True)
                yield "Something went wrong while I was thinking."
                return

            choice = result["choices"][0]
            finish_reason = choice.get("finish_reason", "stop")
            msg = choice.get("message", {})

            if finish_reason != "tool_calls":
                text = (msg.get("content") or "").strip()

                # Some models (e.g. Ollama qwen) output tool calls as JSON text
                # instead of structured tool_calls. Detect and handle this.
                if text and text.strip().startswith('{') and not yielded_anything:
                    intercepted = self._try_execute_text_tool_call(text)
                    if intercepted is not None:
                        msgs.append({"role": "assistant", "content": text})
                        msgs.append({
                            "role": "user",
                            "content": "Result: {}\n\nSummarize in one spoken sentence.".format(
                                intercepted[:500]
                            ),
                        })
                        use_tools = False  # force text-only on next round
                        continue

                # Normal text response — yield sentences
                if text:
                    sentences, remainder = _extract_sentences(text + " ")
                    for s in sentences:
                        yielded_anything = True
                        yield s
                    # Only yield remainder if it looks like actual speech
                    if remainder.strip() and len(remainder.strip()) >= 8:
                        yielded_anything = True
                        yield remainder.strip()
                break

            # Execute tool calls
            tool_calls = msg.get("tool_calls", [])
            if not tool_calls:
                break

            msgs.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls,
            })

            for tc in tool_calls:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except json.JSONDecodeError:
                    args = {}
                result_str = _execute_tool(fn.get("name", ""), args)
                msgs.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": result_str[:3000],
                })

            # On last round, force a text response (no more tools)
            if _round == MAX_TOOL_ROUNDS - 2:
                msgs.append({
                    "role": "user",
                    "content": "Now summarize what you found in 1-2 spoken sentences. No tools.",
                })

        if not yielded_anything:
            yield "I ran into trouble completing that task."

    @staticmethod
    def _try_execute_text_tool_call(text):
        """If text looks like a JSON tool call, execute it and return result.

        Handles models that output {"command": "..."} or {"name": "...", "arguments": ...}
        as plain text instead of structured tool_calls.
        Returns result string if executed, None otherwise.
        """
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None

        # Format: {"command": "..."} — direct shell command
        cmd = parsed.get("command")
        if cmd and isinstance(cmd, str):
            return _run_shell(cmd)

        # Format: {"name": "run_shell", "arguments": {"command": "..."}}
        name = parsed.get("name", "")
        args = parsed.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except Exception:
                args = {}
        if name in ("run_shell", "read_pane") and args:
            return _execute_tool(name, args)

        return None

    def _stream_sse(self, msgs, model, timeout, payload_extra=None):
        """True SSE streaming — yields sentences as tokens arrive.

        Used for quick (no-tool) responses for minimum first-word latency.
        """
        payload = {
            "model": model,
            "messages": msgs,
            "stream": True,
            "max_tokens": 400,
            "temperature": 0.3,
        }
        if payload_extra:
            payload.update(payload_extra)

        try:
            resp = requests.post(
                "{}/chat/completions".format(LITELLM_URL),
                json=payload,
                stream=True,
                timeout=timeout,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        except requests.ConnectionError:
            self._litellm_ok = False
            yield "I lost connection to my language model."
            return
        except Exception as e:
            print("[Brain] SSE connect error: {}".format(e), flush=True)
            yield "Something went wrong while I was thinking."
            return

        text_buf = ""
        try:
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data: "):
                    continue
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    content = chunk["choices"][0].get("delta", {}).get("content") or ""
                    if content:
                        text_buf += content
                        sentences, text_buf = _extract_sentences(text_buf)
                        for s in sentences:
                            yield s
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
        except Exception as e:
            print("[Brain] SSE read error: {}".format(e), flush=True)

        if text_buf.strip():
            yield text_buf.strip()

    # ── Blocking fallback ────────────────────────────────────────────────

    def think(self, user_text, mode="full"):
        """Blocking think — collects all streamed sentences into one string."""
        sentences = list(self.think_streaming(user_text, mode))
        return " ".join(sentences) if sentences else "I had trouble with that."

    # ── Session end ──────────────────────────────────────────────────────

    def save_session_summary(self):
        """Ask Claude to summarize the conversation and save it to persistent memory."""
        if len(self.history) < 2 or not self._ensure_litellm():
            return
        try:
            turns = "\n".join(
                "User: {}\nJarvis: {}".format(h["user"], h["response"])
                for h in self.history[-10:]
            )
            payload = {
                "model": QUICK_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Summarize this conversation in 1-2 sentences, "
                            "focusing on what tasks were completed or topics discussed. "
                            "Be concise. No markdown."
                        )
                    },
                    {"role": "user", "content": turns}
                ],
                "max_tokens": 100,
                "temperature": 0.1,
            }
            resp = _post_completion(payload, timeout=10)
            resp.raise_for_status()
            result = resp.json()
            summary = result["choices"][0]["message"]["content"].strip()
            if summary:
                self.memory.add_session_summary(summary)
                print("[Brain] Session summary saved: {}".format(summary[:80]), flush=True)
        except Exception as e:
            print("[Brain] Failed to save session summary: {}".format(e), flush=True)

    def reset(self):
        """Clear conversation history and save a summary to persistent memory."""
        self.save_session_summary()
        self.history.clear()
