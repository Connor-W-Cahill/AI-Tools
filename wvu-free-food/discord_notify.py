"""Send WVU free food briefing to a Discord channel via webhook."""

from __future__ import annotations
import logging
import os
import re
import requests

logger = logging.getLogger(__name__)

MAX_EMBED_CHARS = 4096
MAX_MESSAGE_CHARS = 2000


def _split_briefing(text: str) -> list[str]:
    """Split briefing into Discord-sized chunks, breaking at section boundaries."""
    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > MAX_EMBED_CHARS and current:
            chunks.append(current.rstrip())
            current = line
        else:
            current += line
    if current.strip():
        chunks.append(current.rstrip())
    return chunks


def _make_discord_summary(briefing_text: str) -> str:
    """Extract a short summary line from the briefing for the embed title."""
    for line in briefing_text.splitlines():
        line = line.strip().lstrip("#").strip()
        if line.startswith("**") and line.endswith("**"):
            return line.strip("*")
        if re.search(r"\d+ (confirmed|food|event)", line, re.I):
            return line.strip("*").strip()
    return "WVU Free Food Briefing"


def post_briefing(briefing_text: str, webhook_url: str, date_str: str) -> bool:
    """
    Post the briefing to Discord.
    Splits into multiple embeds if needed.
    Returns True on success.
    """
    if not webhook_url:
        logger.warning("DISCORD_WEBHOOK_URL not set — skipping Discord notification")
        return False

    summary = _make_discord_summary(briefing_text)
    chunks = _split_briefing(briefing_text)

    # First message: embed with title + first chunk
    first_embed = {
        "title": f"🍕 WVU Free Food — {date_str}",
        "description": chunks[0],
        "color": 0xFFD700,  # gold
        "footer": {"text": "WVU Free Food Scraper • runs daily at 1 PM"},
    }
    payload = {"embeds": [first_embed]}

    try:
        r = requests.post(webhook_url, json=payload, timeout=15)
        r.raise_for_status()
    except requests.RequestException as e:
        logger.error("Discord webhook failed: %s", e)
        return False

    # Remaining chunks as follow-up embeds
    for chunk in chunks[1:]:
        follow = {"embeds": [{"description": chunk, "color": 0xFFD700}]}
        try:
            r = requests.post(webhook_url, json=follow, timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.error("Discord follow-up chunk failed: %s", e)
            return False

    logger.info("Discord notification sent (%d chunk(s))", len(chunks))
    return True
