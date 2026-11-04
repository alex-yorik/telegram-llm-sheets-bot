"""Общая настройка тестов: изолированные настройки без глобального окружения."""

import pytest

from config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Возвращает валидные тестовые настройки без чтения .env и os.environ."""
    return Settings(
        _env_file=None,
        telegram_bot_token="0000000000:TEST_TOKEN",
        llm_api_key="test-llm-key",
        llm_api_base="https://llm.example.test/v1",
        llm_model="gpt-4o-mini",
        llm_timeout_seconds=30,
        google_spreadsheet_id="test-spreadsheet-id",
        google_sheet_name="Sheet1",
        google_application_credentials="/tmp/test-service-account.json",
        log_level="INFO",
    )


@pytest.fixture(autouse=True)
def reset_llm_client():
    """Isolates the shared OpenAI client between tests."""
    import llm

    llm._client = None
    llm._client_signature = None
    yield
    llm._client = None
    llm._client_signature = None


@pytest.fixture(autouse=True)
def reset_handler_state():
    """Изолирует глобальное состояние обработчиков между тестами."""
    import handlers

    handlers.processed_messages.clear()
    handlers.sheets_client = None
    yield
    handlers.processed_messages.clear()
    handlers.sheets_client = None
