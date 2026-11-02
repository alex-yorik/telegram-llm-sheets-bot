"""Общая настройка тестов: фиктивные значения окружения без реальных ключей."""

import os

import pytest

os.environ["TELEGRAM_BOT_TOKEN"] = "0000000000:TEST_TOKEN"
os.environ["LLM_API_KEY"] = "test-llm-key"
os.environ["LLM_API_BASE"] = "https://llm.example.test/v1"
os.environ["GOOGLE_SPREADSHEET_ID"] = "test-spreadsheet-id"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/test-service-account.json"
os.environ["LOG_LEVEL"] = "INFO"


@pytest.fixture(autouse=True)
def reset_handler_state():
    """Изолирует глобальное состояние обработчиков между тестами."""
    import handlers

    handlers.processed_messages.clear()
    handlers.sheets_client = None
    yield
    handlers.processed_messages.clear()
    handlers.sheets_client = None
