"""
Entrypoint for the PokerNow SNG agent.

Usage:
    python run_agent.py
"""

import asyncio
import sys

from browser_use import Browser

from config import Settings
from src.agent import create_agent
from src.overlay import create_overlay_hook


async def main() -> None:
    settings = Settings.from_env()

    browser = Browser(
        allowed_domains=list(settings.browser.allowed_domains),
        keep_alive=True,
    )

    agent = create_agent(settings, browser=browser)
    hook = create_overlay_hook()

    print(
        "\n  The overlay starts PAUSED — log in first, "
        "then toggle it on to let the bot play.\n"
    )

    await agent.run(on_step_start=hook)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgent stopped by user.", file=sys.stderr)
        sys.exit(0)
