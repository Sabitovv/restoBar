import os

from app.config import Settings


def test_settings_bot_mode_defaults_to_webhook(monkeypatch):
    monkeypatch.delenv("BOT_MODE", raising=False)
    settings = Settings.from_env()
    assert settings.bot_mode == "webhook"


def test_settings_bot_mode_is_normalized(monkeypatch):
    monkeypatch.setenv("BOT_MODE", " Polling ")
    settings = Settings.from_env()
    assert settings.bot_mode == "polling"
