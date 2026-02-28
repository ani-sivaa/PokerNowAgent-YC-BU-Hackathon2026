"""
Agent lifecycle management.

Sets up the Browser-Use agent with the correct LLM, browser, tools,
and task prompt. The task prompt combines the SNG navigation
instructions with the full poker strategy guide.
"""

from __future__ import annotations

from browser_use import Agent

from config.settings import Settings
from src.browser import create_browser
from src.strategy import SNGStrategy
from src.tools import configure_tools, tools

NAVIGATION_TASK = """\
1. Go to https://network.pokernow.com/sng_tournaments and ensure you are logged in.
   When you see a CAPTCHA or "verify you are human" challenge:
   - First call the "Solve captcha via API" action.
   - If it returns failure, call "Request human to solve captcha" and wait.
2. On the Friendly Sit & Go page, wait for "Next Tournament Queue" to load
   and join the queue (or join the next tournament when available).
   If a captcha appears when joining, follow the same captcha flow.
3. When a table opens, take your seat. Only Friendly Sit & Go -- do not
   navigate to Lounge or other game modes.
4. For every hand when it is your turn: observe the table state (your cards,
   community cards, pot size, stack sizes, position, and blind level), then
   follow the strategy guide below to decide your action and click the
   appropriate button (fold / check / bet / call / raise / all-in).
5. When the tournament ends, return to the SNG lobby and rejoin the queue.
6. Continue until told to stop, then call done() with a short results summary.
"""


def build_task(table_size: int = 8) -> str:
    """Combine navigation instructions with the full strategy prompt."""
    strategy = SNGStrategy(table_size=table_size).build_prompt()
    return f"{NAVIGATION_TASK}\n{strategy}"


def create_llm(settings: Settings):
    """Instantiate the LLM client based on the configured provider."""
    if settings.llm_provider == "browser_use":
        from browser_use import ChatBrowserUse
        return ChatBrowserUse()

    if settings.llm_provider == "openai":
        from browser_use import ChatOpenAI
        return ChatOpenAI(model="gpt-4.1-mini")

    if settings.llm_provider == "google":
        from browser_use import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    if settings.llm_provider == "anthropic":
        from browser_use import ChatAnthropic
        return ChatAnthropic(model="claude-sonnet-4-20250514")

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


def create_agent(settings: Settings, table_size: int = 8) -> Agent:
    """Wire everything together and return a ready-to-run Agent."""
    configure_tools(settings.captcha)
    llm = create_llm(settings)
    browser = create_browser(settings.browser)
    task = build_task(table_size)

    return Agent(
        task=task,
        llm=llm,
        browser=browser,
        tools=tools,
    )
