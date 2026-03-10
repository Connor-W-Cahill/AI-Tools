"""Generate a free-food briefing using Claude via LiteLLM proxy."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests

logger = logging.getLogger(__name__)


def _build_event_block(events, source_label: str) -> str:
    if not events:
        return ""
    lines = [f"\n### {source_label}"]
    for e in events:
        lines.append(f"- **{e.name}**")
        lines.append(f"  - When: {e.date_str}")
        if hasattr(e, "location") and e.location:
            lines.append(f"  - Where: {e.location}")
        if hasattr(e, "organization") and e.organization:
            lines.append(f"  - Org: {e.organization}")
        desc = e.description[:300].strip() if e.description else ""
        if desc:
            lines.append(f"  - Details: {desc}")
        lines.append(f"  - Food: {', '.join(e.food_mentions)}")
        lines.append(f"  - Link: {e.url}")
    return "\n".join(lines)


def generate_briefing(engage_events: List, cal_events: List, briefings_dir: str = "./briefings") -> str:
    """
    Generate a markdown briefing and save it.
    Returns the briefing text.
    """
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%A, %B %-d, %Y")

    # Separate today vs rest of week
    def is_today(e) -> bool:
        return e.start.date() == now.date()

    engage_today = [e for e in engage_events if is_today(e)]
    engage_week = [e for e in engage_events if not is_today(e)]
    cal_today = [e for e in cal_events if is_today(e)]
    cal_week = [e for e in cal_events if not is_today(e)]

    # Build raw data for the prompt — today only
    raw_data = []
    raw_data.append(_build_event_block(engage_today, "WVU Engage — Today"))
    raw_data.append(_build_event_block(cal_today, "WVU Calendar — Today"))
    raw_data_str = "\n".join(r for r in raw_data if r)

    if not raw_data_str.strip():
        briefing_text = f"# WVU Free Food Briefing — {today_str}\n\nNo free food events found today or this week. Check back tomorrow!\n"
        _save_briefing(briefing_text, briefings_dir, now)
        return briefing_text

    prompt = f"""You are a helpful assistant for a WVU student hunting for free food on campus.

Today is {today_str}.

Below is scraped event data from WVU Engage and the WVU Calendar. Generate a concise daily briefing covering TODAY'S events only — ignore anything not happening today.

Structure:
1. **Bold one-line summary** (e.g. "X free food events on campus today")
2. ## 🍕 Today's Events
   For each event use this exact format:
   ### [Event Name]
   - **Time**: exact time (e.g. 5:00 PM)
   - **Location**: building/room
   - **Topic**: what the event is about (1 sentence)
   - **Hosted by**: org or department
   - **Food**: be specific — if description says "pizza" say pizza; if vague say "refreshments (unspecified)"
   - **Confidence**: X% — explain in 5 words why (e.g. "explicitly says free pizza", "only mentions refreshments", "food mentioned but unclear if free")
   - **Why go**: 1-sentence pitch
   - **Link**: url

   Confidence scoring guide:
   - 90-100%: explicitly says free food/pizza/lunch/dinner with no ambiguity
   - 70-89%: says "refreshments provided" or "food will be served"
   - 50-69%: mentions food in passing or implied by event type
   - Below 50%: very unclear, food keyword matched but context is vague

3. ## 🏆 Top Pick — your single best bet for free food today, one sentence why

If there are no events today, say so clearly.
Be specific about food. Never say just "food" — use what the description actually says.
Do NOT wrap the output in code fences or markdown blocks. Output raw markdown only.

Raw event data:
{raw_data_str}

Generate the briefing now:"""

    try:
        base_url = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000/v1")
        api_key = os.environ.get("LITELLM_API_KEY", "anything")
        model = os.environ.get("LITELLM_MODEL", "claude-sonnet")
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000},
            timeout=120,
        )
        resp.raise_for_status()
        briefing_text = resp.json()["choices"][0]["message"]["content"]
        header = f"# WVU Free Food Briefing — {today_str}\n\n"
        briefing_text = header + briefing_text
    except Exception as e:
        logger.warning("LiteLLM briefing generation failed (%s), using raw format", e)
        briefing_text = _format_raw_briefing(today_str, engage_today, engage_week, cal_today, cal_week)

    _save_briefing(briefing_text, briefings_dir, now)
    return briefing_text


def _format_raw_briefing(today_str: str, engage_today, engage_week, cal_today, cal_week) -> str:
    """Fallback plain formatter if LiteLLM is unavailable."""
    lines = [f"# WVU Free Food Briefing — {today_str}", ""]
    total_today = len(engage_today) + len(cal_today)
    total_week = len(engage_week) + len(cal_week)
    lines.append(f"**{total_today} events today, {total_week} more this week.**")
    lines.append("")

    lines.append("## Today")
    for e in engage_today + cal_today:
        lines += [
            f"### {e.name}",
            f"- **When**: {e.date_str}",
            f"- **Where**: {getattr(e, 'location', 'TBD') or 'TBD'}",
            f"- **Food**: {', '.join(e.food_mentions)}",
            f"- **Link**: {e.url}",
            "",
        ]

    lines.append("## Upcoming This Week")
    for e in sorted(engage_week + cal_week, key=lambda x: x.start):
        lines += [
            f"### {e.name}",
            f"- **When**: {e.date_str}",
            f"- **Where**: {getattr(e, 'location', 'TBD') or 'TBD'}",
            f"- **Food**: {', '.join(e.food_mentions)}",
            f"- **Link**: {e.url}",
            "",
        ]

    return "\n".join(lines)


def _save_briefing(text: str, briefings_dir: str, now: datetime) -> Path:
    out_dir = Path(briefings_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"briefing-{now.strftime('%Y-%m-%d')}.md"
    path = out_dir / filename
    path.write_text(text)
    logger.info("Briefing saved to %s", path)
    return path
