"""
Centralized configuration loaded from environment variables.

All runtime settings are resolved once at startup and passed through
the application as an immutable dataclass, keeping the rest of the
codebase free from os.environ lookups.
"""

import os
import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv


@dataclass(frozen=True)
class CaptchaSettings:
    """CapSolver integration settings."""

    api_key: str | None = None
    api_url: str = "https://api.capsolver.com"
    poll_interval: int = 2
    poll_timeout: int = 120


@dataclass(frozen=True)
class BrowserSettings:
    """Playwright browser restrictions."""

    headless: bool = False
    allowed_domains: tuple[str, ...] = (
        "*.pokernow.com",
        "*.pokernow.club",
        "network.pokernow.com",
        "www.pokernow.com",
        "accounts.google.com",
        "*.google.com",
        "discord.com",
        "*.discord.com",
        "*.facebook.com",
        "api.x.com",
    )


@dataclass(frozen=True)
class Settings:
    """Top-level application configuration."""

    captcha: CaptchaSettings
    browser: BrowserSettings
    llm_provider: str
    llm_api_key: str
    table_size: int = 8
    max_steps: int = 999_999

    @classmethod
    def from_env(cls, env_path: str = ".env") -> "Settings":
        """Build settings from environment variables, exiting on misconfiguration."""
        load_dotenv(env_path)

        llm_provider, llm_api_key = cls._resolve_llm()
        capsolver_key = os.environ.get("CAPSOLVER_API_KEY") or None
        table_size = int(os.environ.get("TABLE_SIZE", "8"))
        max_steps = int(os.environ.get("BROWSER_USE_MAX_STEPS", "999999"))

        headless = os.environ.get("BROWSER_USE_HEADLESS", "").lower() in (
            "1", "true", "yes",
        )

        settings = cls(
            captcha=CaptchaSettings(api_key=capsolver_key),
            browser=BrowserSettings(headless=headless),
            llm_provider=llm_provider,
            llm_api_key=llm_api_key,
            table_size=table_size,
            max_steps=max_steps,
        )
        settings._validate()
        return settings

    def _validate(self) -> None:
        """Sanity-check values that are easy to misconfigure."""
        if not 2 <= self.table_size <= 9:
            print(
                f"Warning: TABLE_SIZE={self.table_size} is outside the "
                "supported range (2-9). Defaulting to 8.",
                file=sys.stderr,
            )
            object.__setattr__(self, "table_size", 8)
        if len(self.llm_api_key) < 8:
            print(
                "Warning: LLM API key looks suspiciously short. "
                "Double-check your .env file.",
                file=sys.stderr,
            )
        if self.captcha.api_key and len(self.captcha.api_key) < 8:
            print(
                "Warning: CAPSOLVER_API_KEY looks suspiciously short.",
                file=sys.stderr,
            )

    @staticmethod
    def _resolve_llm() -> tuple[str, str]:
        """Return the first available LLM provider and its API key."""
        providers = [
            ("browser_use", "BROWSER_USE_API_KEY"),
            ("openai", "OPENAI_API_KEY"),
            ("google", "GOOGLE_API_KEY"),
            ("anthropic", "ANTHROPIC_API_KEY"),
        ]
        for name, env_var in providers:
            key = os.environ.get(env_var)
            if key:
                return name, key

        print(
            "Error: No LLM API key found. Set one of the following in .env:\n"
            "  BROWSER_USE_API_KEY  (recommended)\n"
            "  OPENAI_API_KEY\n"
            "  GOOGLE_API_KEY\n"
            "  ANTHROPIC_API_KEY",
            file=sys.stderr,
        )
        sys.exit(1)
