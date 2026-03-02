"""
Agent lifecycle management.

Sets up the Browser-Use agent with the correct LLM, browser, tools,
and task prompt. The task prompt combines the SNG navigation
instructions with the full poker strategy guide.

Includes a step hook that auto-clicks "I'm Back" before the LLM
even processes -- PokerNow marks you AFK if a turn takes too long,
and waiting for an LLM round-trip to click that button loses another
5+ seconds.
"""

from __future__ import annotations

import logging
from typing import Any

from browser_use import Agent

from config.settings import Settings
from src.browser import create_browser
from src.strategy import SNGStrategy
from src.tools import configure_tools, tools

logger = logging.getLogger(__name__)


async def _auto_click_im_back(agent: Agent) -> None:
    """Hook that runs at the START of every step before the LLM is called.

    If PokerNow has shown the "I'm Back" button (meaning the server
    marked us AFK due to a slow response), click it immediately so we
    re-enter the game without waiting for a full LLM inference cycle.
    """
    try:
        session = agent.browser_session
        page = await session.get_current_page()
        if page is None:
            return
        clicked = await page.evaluate("""() => {
            const buttons = document.querySelectorAll('button, a, [role="button"]');
            for (const b of buttons) {
                const text = (b.textContent || '').trim();
                if (text === "I'm Back" || text === "Im Back" || text === "I'm back") {
                    b.click();
                    return true;
                }
            }
            return false;
        }""")
        if clicked:
            logger.info("auto-clicked 'I'm Back' before LLM step")
    except Exception:
        pass

NAVIGATION_TASK = """\
1. Go to https://network.pokernow.com/sng_tournaments.
   If the page shows a "Login" button or you are not logged in, STOP and
   call "Request human to solve captcha" to wait for the user.  The user
   will log in manually.  Do NOT click any login or OAuth buttons yourself.
   Only proceed once you can see the logged-in Friendly Sit & Go page
   (the "Join on this Tournament" button with no login prompt).
2. When you see a CAPTCHA or "verify you are human" challenge:
   - First call the "Solve captcha via API" action.
   - If it returns failure, call "Request human to solve captcha" and wait.
3. On the Friendly Sit & Go page, wait for "Next Tournament Queue" to load
   and join the queue (or join the next tournament when available).
   If a captcha appears when joining, follow the same captcha flow.
4. When a table opens, take your seat. Only Friendly Sit & Go -- do not
   navigate to Lounge or other game modes.
5. AFK / "I'M BACK" RECOVERY (HIGHEST PRIORITY):
   If you EVER see an "I'm Back" button on screen, click it IMMEDIATELY
   as your very first action -- before doing anything else. PokerNow
   marks you AFK if you take too long on a turn. Clicking "I'm Back"
   re-enters you into the game. Do this BEFORE reading cards, pot, or
   anything else. The system auto-clicks it for you in most cases, but
   if you see it, click it anyway.
6. DETECTING YOUR TURN vs NOT YOUR TURN:
   It is ONLY your turn when action buttons (Fold, Check, Call, Bet, Raise,
   All In) are visible on screen. If you do NOT see any of these buttons,
   it is NOT your turn -- do NOT try to click anything. Just wait 2 seconds
   and check again. Possible reasons the buttons are missing:
     a) It is another player's turn.
     b) You lagged out / timed out -- the game auto-folded for you.
     c) Cards are being dealt or the hand ended.
   In ALL cases: wait 2 seconds (NOT 5), then check for buttons again.
7. CLICKING RULE: Click each button exactly ONCE. If the button disappears
   after clicking, your action went through -- do NOT click it again.
   If the button is still there after 2 seconds, click it one more time.
   Never click the same button 3+ times. If buttons vanish, wait for the
   next hand -- do NOT keep clicking stale elements.
8. When it IS your turn (action buttons are visible): observe the table
   state (your cards, community cards, pot size, stack sizes, position,
   and blind level), then follow the strategy guide to decide your action.
   CRITICAL TIMING: PokerNow gives ~5 seconds per turn.
   To RAISE: click "Raise", then IMMEDIATELY click a size button
   (Min Raise, 1/2 Pot, Pot, or All In), then confirm. All in ONE step.
   To CALL: click the Call button. Read the amount on it first.
   To CHECK: click Check. Check is FREE -- always prefer check over fold
   when no bet is facing you.
   RULE: You CANNOT check when facing a bet or raise. Your options are
   Call, Raise, or Fold only.
   HOW TO CALL: The Call button shows the chip cost (e.g. "Call 200").
   Compare it to the pot. If you have a strong hand (top pair+, two pair,
   flush, straight), CALL. Do NOT fold strong hands to small bets.
9. When the tournament ends, return to the SNG lobby and rejoin the queue.
10. Continue until told to stop, then call done() with a short results summary.
"""


def build_task(table_size: int = 8) -> str:
    """Combine navigation instructions with the full strategy prompt."""
    strategy = SNGStrategy(table_size=table_size).build_prompt()
    return f"{NAVIGATION_TASK}\n{strategy}"


def create_llm(settings: Settings) -> Any:
    """Instantiate the LLM client based on the configured provider.

    Returns a ChatModel instance compatible with browser-use's Agent.
    The concrete type depends on which LLM provider is configured.
    """
    if settings.llm_provider == "browser_use":
        from browser_use import ChatBrowserUse
        return ChatBrowserUse()

    if settings.llm_provider == "openai":
        from browser_use import ChatOpenAI
        model = settings.llm_model or "gpt-4.1-mini"
        return ChatOpenAI(model=model)

    if settings.llm_provider == "google":
        from browser_use import ChatGoogleGenerativeAI
        model = settings.llm_model or "gemini-2.0-flash"
        return ChatGoogleGenerativeAI(model=model)

    if settings.llm_provider == "anthropic":
        from browser_use import ChatAnthropic
        model = settings.llm_model or "claude-sonnet-4-20250514"
        return ChatAnthropic(model=model)

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def create_agent(settings: Settings) -> Agent:
    """Wire everything together and return a ready-to-run Agent."""
    logger.info("initializing agent with provider=%s", settings.llm_provider)
    configure_tools(settings.captcha)
    llm = create_llm(settings)
    browser = create_browser(settings.browser)
    task = build_task(settings.table_size)

    speed_instructions = (
        "SPEED IS CRITICAL. PokerNow gives ~5 seconds per turn. "
        "If you see 'I'm Back', click it FIRST before anything else. "
        "To RAISE: in one step click Raise → size button → confirm. "
        "To CALL: click Call once. To CHECK: click Check once. "
        "CLICK ONCE ONLY. If the button disappears, it worked. "
        "Do NOT click the same button repeatedly. "
        "When waiting for your turn, wait 2 seconds, NOT 5. "
        "Do NOT fold strong made hands (two pair+) to small bets. "
        "If your stack is under 8 BB, you MUST shove with decent hands "
        "or you will blind out and lose. "
        "Keep your reasoning SHORT. Do not write long analyses. "
        "Decide fast: which button to click, click it, done."
    )

    logger.info("agent ready – table_size=%d", settings.table_size)
    return Agent(
        task=task,
        llm=llm,
        browser=browser,
        tools=tools,
        step_timeout=60,
        max_actions_per_step=10,
        max_failures=15,
        flash_mode=True,
        vision_detail_level="low",
        extend_system_message=speed_instructions,
    )
