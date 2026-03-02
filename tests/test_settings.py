"""Tests for config.settings module."""

import os
from unittest.mock import patch

import pytest

from config.settings import BrowserSettings, CaptchaSettings, Settings


class TestSettingsFromEnv:
    def test_resolves_openai_provider(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-test1234567890\n")
        settings = Settings.from_env(str(env_file))
        assert settings.llm_provider == "openai"
        assert settings.llm_api_key == "sk-test1234567890"

    def test_default_table_size(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-test1234567890\n")
        settings = Settings.from_env(str(env_file))
        assert settings.table_size == 8

    @patch.dict(os.environ, {"TABLE_SIZE": "6", "OPENAI_API_KEY": "sk-test1234567890"})
    def test_custom_table_size(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("")
        settings = Settings.from_env(str(env_file))
        assert settings.table_size == 6

    @patch.dict(os.environ, {"TABLE_SIZE": "99", "OPENAI_API_KEY": "sk-test1234567890"})
    def test_invalid_table_size_resets_to_default(self, tmp_path, capsys):
        env_file = tmp_path / ".env"
        env_file.write_text("")
        settings = Settings.from_env(str(env_file))
        assert settings.table_size == 8
        captured = capsys.readouterr()
        assert "outside the supported range" in captured.err

    def test_capsolver_key_optional(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-test1234567890\n")
        settings = Settings.from_env(str(env_file))
        assert settings.captcha.api_key is None

    @patch.dict(os.environ, {"CAPSOLVER_API_KEY": "cap-key12345", "OPENAI_API_KEY": "sk-test1234567890"})
    def test_capsolver_key_loaded(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("")
        settings = Settings.from_env(str(env_file))
        assert settings.captcha.api_key == "cap-key12345"


class TestBrowserSettings:
    def test_default_domains_include_pokernow(self):
        bs = BrowserSettings()
        assert "*.pokernow.com" in bs.allowed_domains

    def test_headless_default_false(self):
        bs = BrowserSettings()
        assert bs.headless is False
