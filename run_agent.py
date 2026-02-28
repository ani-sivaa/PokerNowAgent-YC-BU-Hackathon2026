"""
Entrypoint for the PokerNow SNG agent.

Usage:
    python run_agent.py
"""

import asyncio
import sys

from config import Settings
from src.agent import create_agent


async def main() -> None:
    settings = Settings.from_env()
    agent = create_agent(settings)
    await agent.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgent stopped by user.", file=sys.stderr)
        sys.exit(0)
