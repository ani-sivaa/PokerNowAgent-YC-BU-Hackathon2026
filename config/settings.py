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

    @classmethod
    def from_env(cls, env_path: str = ".env") -> "Settings":
        """Build settings from environment variables, exiting on misconfiguration."""
        load_dotenv(env_path)

        llm_provider, llm_api_key = cls._resolve_llm()
        capsolver_key = os.environ.get("CAPSOLVER_API_KEY") or None

        return cls(
            captcha=CaptchaSettings(api_key=capsolver_key),
            browser=BrowserSettings(),
            llm_provider=llm_provider,
            llm_api_key=llm_api_key,
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
