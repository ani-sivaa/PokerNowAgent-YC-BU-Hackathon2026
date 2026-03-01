"""
Browser configuration for PokerNow sessions.

Creates a restricted Playwright browser instance that can only navigate
to PokerNow domains, preventing the agent from wandering off-site.
"""

import logging

from browser_use import Browser

from config.settings import BrowserSettings

logger = logging.getLogger(__name__)


def create_browser(settings: BrowserSettings) -> Browser:
    """Return a Browser locked to the configured domain allowlist."""
    logger.info(
        "creating browser with %d allowed domains", len(settings.allowed_domains)
    )
    return Browser(allowed_domains=list(settings.allowed_domains))
