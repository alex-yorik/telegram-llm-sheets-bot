"""Тесты загрузки конфигурации."""

import pytest
from pydantic import ValidationError

from config import Settings, load_settings

REQUIRED_ENV = (
    "TELEGRAM_BOT_TOKEN",
    "LLM_API_KEY",
    "GOOGLE_SPREADSHEET_ID",
    "GOOGLE_APPLICATION_CREDENTIALS",
)


def test_settings_reads_environment(monkeypatch):
    """Обязательные значения берутся из окружения."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test")
    monkeypatch.setenv("LLM_API_KEY", "key")
    monkeypatch.setenv("GOOGLE_SPREADSHEET_ID", "sheet-id")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/creds.json")

    settings = Settings(_env_file=None)

    assert settings.telegram_bot_token == "123:test"
    assert settings.llm_api_key == "key"
    assert settings.google_spreadsheet_id == "sheet-id"
    assert settings.google_application_credentials == "/tmp/creds.json"


def test_settings_defaults(monkeypatch):
    """Необязательные параметры имеют безопасные значения по умолчанию."""
    for name in REQUIRED_ENV:
        monkeypatch.setenv(name, "value")
    monkeypatch.delenv("LLM_API_BASE", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("GOOGLE_SHEET_NAME", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    settings = Settings(_env_file=None)

    assert settings.llm_api_base == "https://api.openai.com/v1"
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.llm_timeout_seconds == 30
    assert settings.google_sheet_name == "Sheet1"
    assert settings.log_level == "INFO"


def test_settings_missing_required(monkeypatch):
    """Отсутствие обязательной переменной останавливает загрузку конфига."""
    for name in REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_load_settings_reads_environment(monkeypatch, tmp_path):
    """load_settings явно загружает конфигурацию из окружения."""
    monkeypatch.chdir(tmp_path)
    for name in REQUIRED_ENV:
        monkeypatch.setenv(name, "value")

    loaded = load_settings()

    assert isinstance(loaded, Settings)
    assert loaded.telegram_bot_token == "value"


def test_load_settings_missing_required(monkeypatch, tmp_path):
    """load_settings валидирует обязательные переменные при запуске."""
    monkeypatch.chdir(tmp_path)
    for name in REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError):
        load_settings()
