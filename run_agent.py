"""
Entrypoint for the PokerNow SNG agent.

Usage:
    python run_agent.py
    python run_agent.py --table-size 6
    python run_agent.py -v          # verbose logging
"""

import argparse
import asyncio
import logging
import sys

from config import Settings
from src.agent import create_agent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the PokerNow SNG poker agent.",
    )
    parser.add_argument(
        "--table-size",
        type=int,
        default=None,
        help="Override table size (default: from TABLE_SIZE env or 8)",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable debug-level logging",
    )
    return parser.parse_args()


async def main(args: argparse.Namespace) -> None:
    settings = Settings.from_env()

    if args.table_size is not None:
        settings = Settings(
            captcha=settings.captcha,
            browser=settings.browser,
            llm_provider=settings.llm_provider,
            llm_api_key=settings.llm_api_key,
            table_size=args.table_size,
        )

    agent = create_agent(settings)
    await agent.run()


if __name__ == "__main__":
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("\nAgent stopped by user.", file=sys.stderr)
        sys.exit(0)
    except RuntimeError as exc:
        logging.getLogger(__name__).error("runtime error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logging.getLogger(__name__).exception("unexpected error: %s", exc)
        sys.exit(2)
