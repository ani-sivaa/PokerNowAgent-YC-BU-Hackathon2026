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
from src.overlay import AgentOverlay


async def main() -> None:
    settings = Settings.from_env()

    browser = Browser(
        allowed_domains=list(settings.browser.allowed_domains),
        keep_alive=True,
    )

    overlay = AgentOverlay(browser)
    await overlay.setup("https://network.pokernow.com/sng_tournaments")

    print("\n  Bot is PAUSED — log in, then toggle the overlay to start.\n")

    while True:
        await overlay.wait_for_activation()
        print("  Bot ACTIVATED\n")

        agent = create_agent(
            settings,
            browser=browser,
            should_stop=overlay.should_stop,
            on_new_step=overlay.on_new_step,
        )
        await agent.run()

        if await overlay.check_active():
            print("  Agent run complete.")
            break

        print("\n  Bot PAUSED — toggle the overlay to resume.\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgent stopped by user.", file=sys.stderr)
        sys.exit(0)
