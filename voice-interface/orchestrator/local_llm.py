"""
Local LLM client for fast inference via Ollama.

Used as a first-pass filter before sending requests to Codex.
Handles: intent classification, simple Q&A, summarization.
"""

import json
import urllib.request
import urllib.error
from typing import Optional

OLLAMA_URL = "http://localhost:11434"
MODEL = "qwen2.5:3b"


def _ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def generate(prompt: str, system: str = "", max_tokens: int = 200, timeout: int = 10) -> Optional[str]:
    """Generate a response from the local Ollama model.

    Returns None if Ollama is unavailable or the request fails.
    """
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.3,
        },
    }
    if system:
        payload["system"] = system

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result.get("response", "").strip()
    except Exception as e:
        print(f"[LocalLLM] Error: {e}", flush=True)
        return None


def classify_intent(text: str) -> str:
    """Classify user intent into one of: simple, complex, action, tmux, knowledge.

    - simple: factual questions, greetings, time/date, math, definitions
    - complex: requires reasoning, multi-step, code generation
    - action: desktop control (click, type, open app, etc.)
    - tmux: window management (tell window X, check window, list windows)
    - knowledge: questions about past work, decisions, project context

    Returns the intent string, or 'complex' if classification fails.
    """
    prompt = f"""Classify this voice command into exactly one category:
- simple: greetings, facts, time, math, definitions, yes/no questions
- complex: coding, debugging, multi-step tasks, analysis
- action: desktop control (click, type, open app, move mouse, screenshots)
- tmux: window management (tell window, check window, list windows, switch window)
- knowledge: questions about past work, decisions, what we did before

Command: "{text}"

Reply with ONLY the category name, nothing else."""

    result = generate(prompt, max_tokens=10, timeout=5)
    if result:
        category = result.strip().lower().split()[0].rstrip(".,:")
        if category in ("simple", "complex", "action", "tmux", "knowledge"):
            return category
    return "complex"


def quick_answer(text: str) -> Optional[str]:
    """Try to answer a simple question locally. Returns None if unable."""
    system = (
        "You are Jarvis, a voice AI assistant. "
        "Give a SHORT spoken answer (1-2 sentences max). "
        "No markdown, no code blocks, no bullet points. "
        "Plain conversational English only."
    )
    return generate(text, system=system, max_tokens=100, timeout=8)
