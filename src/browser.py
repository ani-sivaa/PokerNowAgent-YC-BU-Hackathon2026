"""
Browser configuration for PokerNow sessions.

Creates a restricted Playwright browser instance that can only navigate
to PokerNow domains, preventing the agent from wandering off-site.
Uses a speed-optimized profile so the agent can complete multiple
actions (e.g. raise/call flows) within PokerNow's 5-second action timer.
"""

import logging

from browser_use import Browser, BrowserProfile

from config.settings import BrowserSettings

logger = logging.getLogger(__name__)

POKERNOW_BROWSER_PROFILE = BrowserProfile(
    minimum_wait_page_load_time=0.05,
    wait_for_network_idle_page_load_time=0.05,
    wait_between_actions=0.05,
)


def create_browser(settings: BrowserSettings) -> Browser:
    """Return a Browser locked to the configured domain allowlist."""
    logger.info(
        "creating browser (headless=%s) with %d allowed domains",
        settings.headless,
        len(settings.allowed_domains),
    )
    return Browser(
        browser_profile=POKERNOW_BROWSER_PROFILE,
        headless=settings.headless,
        allowed_domains=list(settings.allowed_domains),
    )
