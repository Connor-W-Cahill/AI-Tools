"""Scrape additional WVU event sources for free food.

Sources:
- WVU Events calendar (events.wvu.edu / Localist platform)
- WVU Student Life events
- WVU Mountain Lair events
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup
from typing import List, Optional

logger = logging.getLogger(__name__)

FOOD_RE = re.compile(
    r"free food|pizza|lunch|dinner|breakfast|snacks|refreshments|catered|catering|"
    r"bbq|cookout|food provided|food will be|food served|beverages|donuts|cookies|"
    r"hot dogs|burgers|wings|tacos|sandwiches|subs|come hungry",
    re.IGNORECASE,
)


@dataclass
class CalEvent:
    name: str
    description: str
    location: str
    start: datetime
    url: str
    source: str
    food_mentions: List[str] = field(default_factory=list)

    @property
    def date_str(self) -> str:
        return self.start.strftime("%A, %B %-d at %-I:%M %p")


def _find_mentions(text: str) -> List[str]:
    return list({m.group(0).lower() for m in FOOD_RE.finditer(text)})


# ------------------------------------------------------------------
# WVU Localist calendar (events.wvu.edu)
# ------------------------------------------------------------------

LOCALIST_API = "https://cal.wvu.edu/api/2/events"


def _fetch_localist(days_ahead: int = 7) -> List[CalEvent]:
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)

    params = {
        "start": now.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d"),
        "pp": 100,  # per page
        "page": 1,
    }
    headers = {"Accept": "application/json"}

    events: list[CalEvent] = []
    try:
        resp = requests.get(LOCALIST_API, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        for item in data.get("events", []):
            event_data = item.get("event", item)
            name = event_data.get("title", "")
            description = event_data.get("description_text", "") or event_data.get("description", "") or ""
            location = event_data.get("location_name", "") or ""
            url = event_data.get("localist_url", "") or event_data.get("url", "") or "https://cal.wvu.edu"

            instances = event_data.get("event_instances", [])
            start_str = ""
            if instances:
                inst = instances[0]
                if isinstance(inst, dict):
                    start_str = inst.get("event_instance", inst).get("start", "")
            try:
                start = datetime.fromisoformat(start_str)
            except Exception:
                start = now

            combined = f"{name} {description} {location}"
            mentions = _find_mentions(combined)
            if mentions:
                events.append(CalEvent(
                    name=name,
                    description=description,
                    location=location,
                    start=start,
                    url=url,
                    source="WVU Events Calendar",
                    food_mentions=mentions,
                ))
    except Exception as e:
        logger.warning("Localist calendar fetch failed: %s", e)

    logger.info("Localist: found %d food events", len(events))
    return events


# ------------------------------------------------------------------
# WVU Student Life / simple HTML scrape fallback
# ------------------------------------------------------------------

STUDENT_LIFE_URL = "https://studentlife.wvu.edu/programs-and-services"


def _fetch_student_life() -> List[CalEvent]:
    events: list[CalEvent] = []
    try:
        resp = requests.get(STUDENT_LIFE_URL, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for el in soup.select(".views-row, .event-item, article.event"):
            text = el.get_text(" ", strip=True)
            if FOOD_RE.search(text):
                name_el = el.select_one("h2, h3, .event-title, .title")
                name = name_el.get_text(strip=True) if name_el else text[:80]
                link_el = el.select_one("a[href]")
                url = link_el["href"] if link_el else STUDENT_LIFE_URL
                if url.startswith("/"):
                    url = "https://studentlife.wvu.edu" + url

                events.append(CalEvent(
                    name=name,
                    description=text[:500],
                    location="",
                    start=datetime.now(timezone.utc),
                    url=url,
                    source="WVU Student Life",
                    food_mentions=_find_mentions(text),
                ))
    except Exception as e:
        logger.warning("Student Life scrape failed: %s", e)

    logger.info("Student Life: found %d food events", len(events))
    return events


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def fetch_all(days_ahead: int = 7) -> List[CalEvent]:
    events = []
    events.extend(_fetch_localist(days_ahead))
    events.extend(_fetch_student_life())
    return events
