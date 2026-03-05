#!/usr/bin/env python3
"""WVU Free Food Scraper — main entry point.

Scrapes WVU Engage + WVU Calendar for events with free food,
then generates a daily briefing via Claude.

Usage:
    python3 main.py               # run scraper + generate briefing
    python3 main.py --print-only  # print briefing to stdout only
    python3 main.py --force-auth  # force re-login (clear saved session)
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project dir
load_dotenv(Path(__file__).parent / ".env")

from auth import WVUAuth
from briefing import generate_briefing
from engage_scraper import fetch_events as fetch_engage_events
from wvu_calendar_scraper import fetch_all as fetch_calendar_events

ENGAGE_URL = "https://wvu.campuslabs.com/engage"
LOG_FILE = Path(__file__).parent / "logs" / "wvu-food.log"
BRIEFINGS_DIR = os.environ.get("BRIEFINGS_DIR", str(Path(__file__).parent / "briefings"))


def setup_logging(verbose: bool = False) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="WVU Free Food Scraper")
    parser.add_argument("--print-only", action="store_true", help="Print briefing to stdout only")
    parser.add_argument("--force-auth", action="store_true", help="Force re-authentication")
    parser.add_argument("--days", type=int, default=7, help="Days ahead to scrape (default: 7)")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger("main")

    username = os.environ.get("WVU_USERNAME", "")
    password = os.environ.get("WVU_PASSWORD", "")

    if not username or not password:
        logger.error("WVU_USERNAME and WVU_PASSWORD must be set in .env")
        sys.exit(1)

    if args.force_auth:
        session_file = Path(__file__).parent / "session" / "cookies.json"
        session_file.unlink(missing_ok=True)
        logger.info("Cleared saved session")

    # ----------------------------------------------------------------
    # Step 1: Try public Engage API (no auth needed)
    # ----------------------------------------------------------------
    logger.info("=== WVU Free Food Scraper ===")
    logger.info("Fetching Engage events (public API)...")
    engage_events = fetch_engage_events(days_ahead=args.days)

    # ----------------------------------------------------------------
    # Step 2: If public API returned nothing, try authenticated access
    # ----------------------------------------------------------------
    if not engage_events:
        logger.info("Public API returned no food events — trying authenticated access")
        headless = os.environ.get("HEADLESS", "true").lower() != "false"
        timeout = int(os.environ.get("BROWSER_TIMEOUT", "30000"))

        auth = WVUAuth(username, password, headless=headless, timeout=timeout)
        try:
            auth.start()
            ok = auth.login(ENGAGE_URL)
            if not ok:
                logger.error("Authentication failed")
                sys.exit(1)

            from engage_scraper import fetch_events_authenticated
            engage_events = fetch_events_authenticated(auth.page(), days_ahead=args.days)
        finally:
            auth.close()

    # ----------------------------------------------------------------
    # Step 3: Scrape WVU calendar (always public)
    # ----------------------------------------------------------------
    logger.info("Fetching WVU Calendar events...")
    cal_events = fetch_calendar_events(days_ahead=args.days)

    # ----------------------------------------------------------------
    # Step 4: Generate briefing
    # ----------------------------------------------------------------
    total = len(engage_events) + len(cal_events)
    logger.info("Total food events found: %d", total)

    briefing = generate_briefing(engage_events, cal_events, briefings_dir=BRIEFINGS_DIR)

    if args.print_only:
        print(briefing)
    else:
        print("\n" + "=" * 60)
        print(briefing)
        print("=" * 60 + "\n")

    logger.info("Done.")


if __name__ == "__main__":
    main()
