"""
Browser-Use custom tool registrations.

Each @tools.action becomes an action the LLM agent can invoke during
a browsing session. We keep the tool definitions thin -- heavy logic
lives in the captcha and strategy sub-packages.
"""

import logging

from browser_use import Tools

try:
    from browser_use import ActionResult
except ImportError:
    from browser_use.agent.views import ActionResult

from browser_use.browser.session import BrowserSession

from config.settings import CaptchaSettings
from src.captcha.human import prompt_human_solve
from src.captcha.solver import solve_captcha

logger = logging.getLogger(__name__)

tools = Tools()

_captcha_settings: CaptchaSettings | None = None


def configure_tools(captcha: CaptchaSettings) -> None:
    """Inject runtime configuration before the agent starts."""
    global _captcha_settings
    _captcha_settings = captcha


@tools.action(
    description=(
        "Try to solve a CAPTCHA or 'verify you are human' challenge on the "
        "current page using CapSolver API. Call this first when you see a "
        "reCAPTCHA. If it fails, use 'Request human to solve captcha' instead."
    ),
    allowed_domains=["*"],
)
async def solve_captcha_via_api(browser_session: BrowserSession) -> ActionResult:
    """Attempt automatic reCAPTCHA v2 solving through CapSolver."""
    logger.info("solve_captcha_via_api invoked")
    if _captcha_settings is None or not _captcha_settings.api_key:
        return ActionResult(
            success=False,
            error=(
                "CAPSOLVER_API_KEY not configured. "
                "Use 'Request human to solve captcha' instead."
            ),
        )

    success, message = await solve_captcha(
        browser_session,
        api_key=_captcha_settings.api_key,
        api_url=_captcha_settings.api_url,
        poll_interval=_captcha_settings.poll_interval,
        poll_timeout=_captcha_settings.poll_timeout,
    )
    if success:
        return ActionResult(success=True, extracted_content=message)
    return ActionResult(success=False, error=message)


@tools.action(
    description=(
        "Ask a human to solve the CAPTCHA visible in the browser. "
        "Use this when automatic solving failed or is unavailable. "
        "The agent will pause until the human confirms."
    ),
    allowed_domains=["*"],
)
async def request_human_solve_captcha() -> ActionResult:
    """Block until the operator confirms the captcha is solved."""
    logger.info("request_human_solve_captcha invoked")
    success, message = await prompt_human_solve()
    if success:
        return ActionResult(success=True, extracted_content=message)
    return ActionResult(success=False, error=message)
