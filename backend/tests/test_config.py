import os
import pytest


def test_settings_loads_defaults():
    from app.config import Settings

    s = Settings(
        _env_file=None,
        openrouter_api_key="test-key",
        telegram_bot_token="test-bot",
        telegram_chat_id="12345",
        pwa_access_token="test-token",
        session_secret_key="test-secret",
    )
    assert s.openrouter_model == "anthropic/claude-opus-4.5"
    assert s.match_threshold == 65
    assert s.scan_interval_hours == 4
    assert s.database_url == "sqlite:///./jobfinder.db"
    assert s.pwa_base_url == "http://localhost:8000"


def test_settings_overrides_from_env(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o")
    monkeypatch.setenv("MATCH_THRESHOLD", "80")
    monkeypatch.setenv("SCAN_INTERVAL_HOURS", "2")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "bot-tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "999")
    monkeypatch.setenv("PWA_ACCESS_TOKEN", "tok123")
    monkeypatch.setenv("PWA_BASE_URL", "http://myvm:8000")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    monkeypatch.setenv("SESSION_SECRET_KEY", "test-secret")

    from app.config import Settings

    s = Settings()
    assert s.openrouter_api_key == "sk-test"
    assert s.openrouter_model == "openai/gpt-4o"
    assert s.match_threshold == 80
    assert s.scan_interval_hours == 2
    assert s.telegram_bot_token == "bot-tok"
    assert s.telegram_chat_id == "999"
    assert s.pwa_access_token == "tok123"
    assert s.pwa_base_url == "http://myvm:8000"
    assert s.database_url == "sqlite:///./test.db"


def test_match_threshold_bounds():
    from app.config import Settings

    with pytest.raises(Exception):
        Settings(
            _env_file=None,
            openrouter_api_key="k",
            telegram_bot_token="t",
            telegram_chat_id="1",
            pwa_access_token="t",
            session_secret_key="test-secret",
            match_threshold=150,
        )
