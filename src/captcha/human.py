"""
Human-in-the-loop captcha fallback.

When automatic solving fails or is unavailable, this module prompts the
operator to solve the captcha manually in the browser window and press
Enter to let the agent continue.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def prompt_human_solve() -> tuple[bool, str]:
    """
    Block until the operator presses Enter.

    Runs the blocking input() call in a thread executor so the async
    event loop stays responsive.
    """
    logger.info("waiting for human to solve captcha in browser")
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: input(
                "\n[captcha] Solve the CAPTCHA in the browser, "
                "then press Enter to continue... "
            ),
        )
    except EOFError:
        logger.warning("non-interactive terminal, cannot prompt user")
        return False, "Non-interactive terminal; cannot prompt for captcha"

    logger.info("human confirmed captcha solved")
    return True, "Human confirmed CAPTCHA solved"
