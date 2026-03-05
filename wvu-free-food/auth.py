"""WVU SSO / Okta authentication using Playwright.

Mirrors the blackboard-downloader auth pattern:
1. Navigate to target URL → redirects to WVU SSO
2. Auto-fill username + password on Okta
3. Click "Send Push" → user approves on phone
4. Save session cookies; reuse for 24 h
"""

import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from typing import Optional
from playwright.sync_api import sync_playwright, Browser, Page, Playwright

logger = logging.getLogger(__name__)

SESSION_FILE = Path(__file__).parent / "session" / "cookies.json"
SESSION_TTL_HOURS = 20  # re-auth after this many hours


class WVUAuth:
    def __init__(self, username: str, password: str, headless: bool = True, timeout: int = 30000):
        self.username = username
        self.password = password
        self.headless = headless
        self.timeout = timeout
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        self._page = self._browser.new_page()
        self._page.set_viewport_size({"width": 1280, "height": 800})
        self._page.set_extra_http_headers({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })

    def login(self, target_url: str) -> bool:
        """Ensure the browser is authenticated. Returns True on success."""
        if self._restore_session():
            logger.info("Restored saved session")
            self._page.goto(target_url, wait_until="networkidle", timeout=self.timeout)
            if self._is_logged_in():
                logger.info("Session valid")
                return True
            logger.info("Session expired, re-authenticating")

        return self._do_login(target_url)

    def page(self) -> Page:
        return self._page

    def close(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    # ------------------------------------------------------------------
    # Internal login flow
    # ------------------------------------------------------------------

    def _do_login(self, target_url: str) -> bool:
        logger.info(f"Navigating to {target_url}")
        self._page.goto(target_url, wait_until="networkidle", timeout=self.timeout)

        # Follow SSO redirects to Okta
        self._wait_for_okta()

        if not self._fill_okta_credentials():
            return False

        if not self._handle_mfa():
            return False

        # Wait to land back on the original site
        try:
            self._page.wait_for_url("*campuslabs.com*", timeout=30000)
        except Exception:
            pass

        if self._is_logged_in():
            self._save_session()
            return True

        logger.error("Login verification failed")
        return False

    def _wait_for_okta(self) -> None:
        try:
            self._page.wait_for_url("*okta*", timeout=15000)
            logger.info("Redirected to Okta")
        except Exception:
            logger.debug("No Okta redirect detected (may already be logged in)")

    def _fill_okta_credentials(self) -> bool:
        page = self._page

        # Username field
        try:
            page.wait_for_selector('input[name="identifier"], input[type="email"], #okta-signin-username', timeout=10000)
        except Exception:
            logger.warning("Could not find Okta username field")
            return False

        username_field = (
            page.query_selector('input[name="identifier"]')
            or page.query_selector('input[type="email"]')
            or page.query_selector('#okta-signin-username')
        )
        if not username_field:
            return False

        username_field.triple_click()
        username_field.type(self.username, delay=50)
        logger.info("Entered username")

        # Click Next
        next_btn = (
            page.query_selector('input[value="Next"]')
            or page.query_selector('button:has-text("Next")')
        )
        if next_btn:
            next_btn.click()
            page.wait_for_load_state("networkidle")
            time.sleep(1)

        # Password field
        try:
            page.wait_for_selector('input[type="password"], #okta-signin-password', timeout=10000)
        except Exception:
            logger.warning("Could not find Okta password field")
            return False

        pw_field = (
            page.query_selector('input[type="password"]')
            or page.query_selector('#okta-signin-password')
        )
        if not pw_field:
            return False

        pw_field.triple_click()
        pw_field.type(self.password, delay=50)
        logger.info("Entered password")

        # Sign in
        sign_in = (
            page.query_selector('input[value="Sign In"]')
            or page.query_selector('button:has-text("Sign In")')
            or page.query_selector('button:has-text("Verify")')
            or page.query_selector('#okta-signin-submit')
        )
        if sign_in:
            sign_in.click()
            page.wait_for_load_state("networkidle")
            time.sleep(2)

        return True

    def _handle_mfa(self) -> bool:
        page = self._page

        # Try to click "Send Push" automatically
        try:
            page.wait_for_selector('text="Send Push"', timeout=8000)
            push_btn = page.query_selector('text="Send Push"')
            if push_btn:
                push_btn.click()
                logger.info("Sent Okta push notification")
                self._print_mfa_banner()
                return self._poll_for_mfa_completion()
        except Exception:
            pass

        # Look for any MFA-related page
        if "okta" in page.url().lower() or "mfa" in page.url().lower():
            self._print_manual_mfa_banner()
            input("Press Enter after approving MFA on your phone...")
            time.sleep(2)
            page.wait_for_load_state("networkidle")
            return True

        # May have already passed MFA
        return True

    def _poll_for_mfa_completion(self, timeout_s: int = 120) -> bool:
        start = time.time()
        while time.time() - start < timeout_s:
            time.sleep(3)
            url = self._page.url()
            if "okta" not in url.lower():
                logger.info("MFA approved, redirected away from Okta")
                self._page.wait_for_load_state("networkidle")
                return True
        logger.error("MFA timed out after %ds", timeout_s)
        return False

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def _save_session(self) -> None:
        cookies = self._page.context.cookies()
        data = {"cookies": cookies, "saved_at": datetime.utcnow().isoformat()}
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        SESSION_FILE.write_text(json.dumps(data, indent=2))
        logger.info("Session saved to %s", SESSION_FILE)

    def _restore_session(self) -> bool:
        if not SESSION_FILE.exists():
            return False
        try:
            data = json.loads(SESSION_FILE.read_text())
            saved_at = datetime.fromisoformat(data["saved_at"])
            if datetime.utcnow() - saved_at > timedelta(hours=SESSION_TTL_HOURS):
                logger.info("Session too old, will re-authenticate")
                SESSION_FILE.unlink(missing_ok=True)
                return False
            self._page.context.add_cookies(data["cookies"])
            return True
        except Exception as e:
            logger.warning("Failed to restore session: %s", e)
            return False

    def _is_logged_in(self) -> bool:
        url = self._page.url()
        return "okta" not in url.lower() and "login" not in url.lower()

    # ------------------------------------------------------------------
    # UI banners
    # ------------------------------------------------------------------

    @staticmethod
    def _print_mfa_banner() -> None:
        print("\n" + "=" * 60)
        print("  OKTA PUSH SENT — approve on your phone")
        print("  Waiting up to 2 minutes...")
        print("=" * 60 + "\n")

    @staticmethod
    def _print_manual_mfa_banner() -> None:
        print("\n" + "=" * 60)
        print("  MFA REQUIRED — complete in browser")
        print("  Then press Enter to continue")
        print("=" * 60 + "\n")
