"""Scrape WVU Engage for events that mention free food.

Tries the public Campus Labs JSON API first (no auth needed).
Falls back to authenticated browser scraping if needed.
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import requests
from typing import List, Optional

logger = logging.getLogger(__name__)

ENGAGE_BASE = "https://wvu.campuslabs.com/engage"
ENGAGE_API = f"{ENGAGE_BASE}/api/discovery/event/search"

# Keywords that suggest free food is present
FOOD_KEYWORDS = [
    "free food", "food provided", "pizza", "lunch", "dinner", "breakfast",
    "snacks", "refreshments", "light refreshments", "food will be",
    "catering", "catered", "bbq", "cookout", "potluck", "bring food",
    "food and drinks", "beverages", "wings", "tacos", "sandwiches",
    "donuts", "cookies", "cake", "fruit", "veggie", "sub", "subs",
    "hot dogs", "burgers", "food served", "we will have food",
    "come hungry", "eat", "meal", "dining",
]

FOOD_RE = re.compile("|".join(re.escape(k) for k in FOOD_KEYWORDS), re.IGNORECASE)


@dataclass
class Event:
    id: str
    name: str
    description: str
    location: str
    start: datetime
    end: datetime
    organization: str
    url: str
    food_mentions: List[str] = field(default_factory=list)

    @property
    def date_str(self) -> str:
        return self.start.strftime("%A, %B %-d at %-I:%M %p")


def _find_food_mentions(text: str) -> List[str]:
    return list({m.group(0).lower() for m in FOOD_RE.finditer(text)})


def _parse_event(raw: dict) -> Optional[Event]:
    try:
        start = datetime.fromisoformat(raw["startsOn"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(raw["endsOn"].replace("Z", "+00:00"))
        description = raw.get("description", "") or ""
        name = raw.get("name", "") or ""
        location = raw.get("location", "") or ""
        org = ""
        if raw.get("organizationName"):
            org = raw["organizationName"]
        elif raw.get("theme", {}).get("organizationName"):
            org = raw["theme"]["organizationName"]

        combined_text = f"{name} {description} {location}"
        mentions = _find_food_mentions(combined_text)

        event_id = str(raw.get("id", ""))
        url = f"{ENGAGE_BASE}/event/{event_id}" if event_id else f"{ENGAGE_BASE}/events"

        return Event(
            id=event_id,
            name=name,
            description=description,
            location=location,
            start=start,
            end=end,
            organization=org,
            url=url,
            food_mentions=mentions,
        )
    except Exception as e:
        logger.debug("Failed to parse event: %s — %s", raw.get("name"), e)
        return None


def _fetch_api_page(starts_after: str, ends_before: str, skip: int = 0, take: int = 100) -> dict:
    params = {
        "endsAfter": starts_after,
        "startsBefore": ends_before,
        "orderByField": "StartsOn",
        "orderByDirection": "Ascending",
        "status": "Approved",
        "take": take,
        "skip": skip,
    }
    headers = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; WVUFoodBot/1.0)",
        "Referer": ENGAGE_BASE,
    }
    resp = requests.get(ENGAGE_API, params=params, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.json()


def fetch_events(days_ahead: int = 7) -> List[Event]:
    """Fetch all Engage events for the next `days_ahead` days, filter for food."""
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)

    starts_after = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    ends_before = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    all_events: list[Event] = []
    skip = 0
    take = 100

    logger.info("Fetching Engage events: %s → %s", starts_after, ends_before)

    while True:
        try:
            data = _fetch_api_page(starts_after, ends_before, skip, take)
        except requests.HTTPError as e:
            logger.error("Engage API error: %s", e)
            break
        except Exception as e:
            logger.error("Failed to fetch Engage events: %s", e)
            break

        items = data.get("value", [])
        if not items:
            break

        for raw in items:
            event = _parse_event(raw)
            if event:
                all_events.append(event)

        total = data.get("@odata.count", len(all_events))
        skip += take
        if skip >= total:
            break

        time.sleep(0.5)  # be polite

    logger.info("Fetched %d total events from Engage", len(all_events))

    food_events = [e for e in all_events if e.food_mentions]
    logger.info("Found %d events with food mentions", len(food_events))
    return food_events


def fetch_events_authenticated(page, days_ahead: int = 7) -> List[Event]:
    """
    Fallback: use an authenticated Playwright page to hit the API with session cookies.
    Only needed if the public API starts requiring auth.
    """
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days_ahead)
    starts_after = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    ends_before = end.strftime("%Y-%m-%dT%H:%M:%SZ")

    url = (
        f"{ENGAGE_API}?endsAfter={starts_after}&startsBefore={ends_before}"
        f"&orderByField=StartsOn&orderByDirection=Ascending&status=Approved&take=200&skip=0"
    )

    response = page.goto(url, wait_until="networkidle")
    raw = response.json()
    events = []
    for item in raw.get("value", []):
        event = _parse_event(item)
        if event and event.food_mentions:
            events.append(event)
    return events
