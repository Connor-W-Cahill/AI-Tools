"""
Screen awareness — gathers info about open windows, active app, and can
take/OCR screenshots. Includes GPT-4o vision for true screen understanding.
"""

import base64
import json
import os
import subprocess
import tempfile
import time
from typing import Optional

import openai


SCREENSHOT_DIR = "/tmp/orchestrator_screenshots"
CODEX_AUTH = os.path.expanduser("~/.codex/auth.json")


def _get_openai_token() -> Optional[str]:
    """Read OpenAI access token from Codex auth."""
    try:
        with open(CODEX_AUTH, 'r') as f:
            data = json.load(f)
        return data.get("tokens", {}).get("access_token")
    except Exception:
        return None


def get_mouse_position() -> str:
    """Get current mouse cursor position via xdotool."""
    try:
        r = subprocess.run(
            ["xdotool", "getmouselocation", "--shell"],
            capture_output=True, text=True, timeout=3,
            env={**os.environ, "DISPLAY": ":0"}
        )
        if r.returncode == 0:
            x = y = ""
            for line in r.stdout.splitlines():
                if line.startswith("X="):
                    x = line.split("=", 1)[1]
                elif line.startswith("Y="):
                    y = line.split("=", 1)[1]
            if x and y:
                return f"Mouse: ({x}, {y})"
    except Exception:
        pass
    return ""


_screen_geometry_cache: Optional[str] = None


def get_screen_geometry() -> str:
    """Get screen resolution via xdpyinfo. Cached (resolution doesn't change mid-session)."""
    global _screen_geometry_cache
    if _screen_geometry_cache is not None:
        return _screen_geometry_cache
    try:
        r = subprocess.run(
            ["xdpyinfo"],
            capture_output=True, text=True, timeout=3,
            env={**os.environ, "DISPLAY": ":0"}
        )
        if r.returncode == 0:
            for line in r.stdout.splitlines():
                if "dimensions:" in line:
                    # e.g. "  dimensions:    1920x1080 pixels (508x285 millimeters)"
                    parts = line.split()
                    idx = parts.index("dimensions:") if "dimensions:" in parts else -1
                    if idx >= 0 and idx + 1 < len(parts):
                        _screen_geometry_cache = f"Screen: {parts[idx + 1]}"
                        return _screen_geometry_cache
    except Exception:
        pass
    return ""


def get_windows() -> str:
    """List all open windows with their titles."""
    try:
        r = subprocess.run(
            ["wmctrl", "-l", "-p"],
            capture_output=True, text=True, timeout=3,
            env={**os.environ, "DISPLAY": ":0"}
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def get_active_window() -> str:
    """Get the currently focused window name."""
    try:
        r = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowname"],
            capture_output=True, text=True, timeout=3,
            env={**os.environ, "DISPLAY": ":0"}
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def take_screenshot() -> str:
    """Take a screenshot and return the file path."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    path = os.path.join(SCREENSHOT_DIR, f"screen_{int(time.time())}.png")
    try:
        r = subprocess.run(
            ["scrot", path],
            capture_output=True, text=True, timeout=5,
            env={**os.environ, "DISPLAY": ":0"}
        )
        if r.returncode == 0 and os.path.exists(path):
            return path
    except Exception:
        pass
    return ""


def ocr_screenshot(image_path: str) -> str:
    """Extract text from a screenshot using tesseract OCR."""
    if not image_path or not os.path.exists(image_path):
        return ""
    try:
        r = subprocess.run(
            ["tesseract", image_path, "stdout", "--psm", "3"],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode == 0:
            return r.stdout.strip()
    except Exception:
        pass
    return ""


def vision_describe(image_path: str, question: str = "Describe what you see on this screen.") -> str:
    """Use GPT-4o to analyze a screenshot with true vision understanding."""
    token = _get_openai_token()
    if not token:
        return ""

    if not image_path or not os.path.exists(image_path):
        return ""

    try:
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        client = openai.OpenAI(api_key=token)
        resp = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{question} Keep your answer to 2-3 short sentences for voice readback."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}", "detail": "low"}}
                ]
            }]
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[Screen] Vision API error: {e}", flush=True)
        return ""


def get_screen_context(include_windows: bool = True, include_geometry: bool = False) -> str:
    """Build a text summary of what's on screen for the brain.

    Args:
        include_windows: Include full window list (adds ~50ms).
        include_geometry: Include screen resolution.
    """
    parts = []

    active = get_active_window()
    if active:
        parts.append(f"Active window: {active}")

    mouse = get_mouse_position()
    if mouse:
        parts.append(mouse)

    if include_geometry:
        geom = get_screen_geometry()
        if geom:
            parts.append(geom)

    if include_windows:
        windows = get_windows()
        if windows:
            lines = []
            for line in windows.splitlines():
                cols = line.split(None, 4)
                if len(cols) >= 5:
                    lines.append(f"  - {cols[4]}")
                elif len(cols) >= 4:
                    lines.append(f"  - {cols[3]}")
            if lines:
                parts.append("Open windows:\n" + "\n".join(lines))

    return "\n".join(parts) if parts else "No screen info available."


def get_screen_context_with_vision(question: str = "") -> str:
    """Full screen context with vision analysis (GPT-4o) or OCR fallback."""
    ctx = get_screen_context()

    path = take_screenshot()
    if not path:
        return ctx

    # Try GPT-4o vision first
    q = question or "Describe what is visible on this screen — applications, content, and what the user appears to be doing."
    vision_result = vision_describe(path, q)
    if vision_result:
        ctx += f"\n\nScreen vision analysis:\n{vision_result}"
    else:
        # Fallback to OCR
        ocr_text = ocr_screenshot(path)
        if ocr_text:
            if len(ocr_text) > 1500:
                ocr_text = ocr_text[:1500] + "..."
            ctx += f"\n\nVisible screen text (OCR):\n{ocr_text}"

    try:
        os.unlink(path)
    except OSError:
        pass

    return ctx
