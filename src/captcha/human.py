"""
Human-in-the-loop captcha fallback.

When automatic solving fails or is unavailable, this module prompts the
operator to solve the captcha manually in the browser window and press
Enter to let the agent continue.
"""

import asyncio


async def prompt_human_solve() -> tuple[bool, str]:
    """
    Block until the operator presses Enter.

    Runs the blocking input() call in a thread executor so the async
    event loop stays responsive.
    """
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: input(
                "\n[captcha] Solve the CAPTCHA in the browser, "
                "then press Enter to continue... "
            ),
        )
    except EOFError:
        return False, "Non-interactive terminal; cannot prompt for captcha"

    return True, "Human confirmed CAPTCHA solved"
