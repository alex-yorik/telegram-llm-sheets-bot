"""Тесты приватности логирования: реальные Telegram ID и текст не попадают в логи."""

import logging
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import handlers
from handlers import handle_text
from llm import extract_lead
from models import Lead
from sheets import HEADER, GoogleSheetsClient, SheetsError

CORRELATION_RE = re.compile(r"correlation_id=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
CHAT_ID = 987654321
USER_ID = 555444333


def make_update(
    text: str = "hello",
    message_id: int = 1,
    chat_id: int | None = CHAT_ID,
):
    """Создает мок Update с реальными по форме Telegram ID."""
    update = MagicMock()
    message = MagicMock()
    message.text = text
    message.message_id = message_id
    message.reply_text = AsyncMock()
    update.message = message
    if chat_id is not None:
        update.effective_chat = MagicMock()
        update.effective_chat.id = chat_id
    else:
        update.effective_chat = None
    update.effective_user = MagicMock()
    update.effective_user.id = USER_ID
    update.effective_user.username = "private_username"
    update.effective_user.first_name = "Private"
    update.effective_user.last_name = "Person"
    return update


def make_context(client=None):
    """Создает мок Context с bot_data."""
    context = MagicMock()
    context.bot_data = {}
    if client is not None:
        context.bot_data["sheets_client"] = client
    return context


def build_sheets_client() -> GoogleSheetsClient:
    """Создает клиент Sheets с замоканными credentials и gspread."""
    with (
        patch("sheets.Credentials.from_service_account_file") as credentials,
        patch("sheets.gspread.authorize") as authorize,
    ):
        credentials.return_value = MagicMock()
        authorize.return_value = MagicMock()
        return GoogleSheetsClient(
            credentials_path="/tmp/fake-credentials.json",
            spreadsheet_id="test-spreadsheet-id",
            sheet_name="Sheet1",
        )


def assert_no_telegram_ids(caplog) -> None:
    """Ни один лог не содержит chat_id/user_id или профиль пользователя."""
    assert str(CHAT_ID) not in caplog.text
    assert str(USER_ID) not in caplog.text
    assert "private_username" not in caplog.text
    assert "Private Person" not in caplog.text


@pytest.mark.asyncio
async def test_handle_text_does_not_log_chat_id(caplog):
    """Успешная обработка не пишет реальный chat_id в логи."""
    caplog.set_level(logging.INFO, logger="handlers")

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")
        await handle_text(make_update(), make_context(MagicMock()))

    assert_no_telegram_ids(caplog)


@pytest.mark.asyncio
async def test_duplicate_does_not_log_chat_id(caplog):
    """Пропуск дубля не пишет реальный chat_id в логи."""
    caplog.set_level(logging.INFO, logger="handlers")
    context = make_context(MagicMock())

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")
        await handle_text(make_update(message_id=7), context)
        await handle_text(make_update(message_id=7), context)

    assert "Duplicate message received" in caplog.text
    assert_no_telegram_ids(caplog)


@pytest.mark.asyncio
async def test_long_message_does_not_log_chat_id(caplog, monkeypatch):
    """Отказ по длине не пишет реальный chat_id в логи."""
    caplog.set_level(logging.INFO, logger="handlers")
    monkeypatch.setattr(handlers, "MAX_MESSAGE_LENGTH", 10)

    await handle_text(make_update(text="a" * 11), make_context())

    assert "too long" in caplog.text
    assert_no_telegram_ids(caplog)


@pytest.mark.asyncio
async def test_sheets_error_does_not_log_chat_id(caplog):
    """Ошибка сохранения не пишет реальный chat_id в логи."""
    caplog.set_level(logging.INFO, logger="handlers")
    client = MagicMock()
    client.append_lead.side_effect = SheetsError("Sheets Error")

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")
        await handle_text(make_update(), make_context(client))

    assert "Failed to save lead" in caplog.text
    assert_no_telegram_ids(caplog)


@pytest.mark.asyncio
async def test_message_content_is_not_logged(caplog):
    """Содержимое сообщения не пишется в логи."""
    caplog.set_level(logging.INFO, logger="handlers")
    secret_text = "MY-SECRET-MESSAGE-CONTENT-42"

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")
        await handle_text(make_update(text=secret_text), make_context(MagicMock()))

    assert secret_text not in caplog.text


@pytest.mark.asyncio
async def test_correlation_id_links_one_request(caplog):
    """Все события одного запроса используют один и тот же correlation_id."""
    caplog.set_level(logging.INFO, logger="handlers")

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")
        await handle_text(make_update(), make_context(MagicMock()))

    ids = CORRELATION_RE.findall(caplog.text)
    assert len(ids) >= 2
    assert len(set(ids)) == 1


@pytest.mark.asyncio
async def test_correlation_id_differs_between_requests(caplog):
    """Разные запросы получают разные correlation_id."""
    caplog.set_level(logging.INFO, logger="handlers")
    context = make_context(MagicMock())

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")
        await handle_text(make_update(message_id=1), context)
        await handle_text(make_update(message_id=2), context)

    ids = set(CORRELATION_RE.findall(caplog.text))
    assert len(ids) == 2


@pytest.mark.asyncio
async def test_extract_lead_logs_correlation_id_not_content(caplog):
    """LLM-слой пишет correlation_id, но не текст сообщения."""
    caplog.set_level(logging.INFO, logger="llm")
    secret_text = "MY-SECRET-MESSAGE-CONTENT-99"
    message = MagicMock(content='{"name": "John"}')
    response = MagicMock()
    response.choices = [MagicMock(message=message)]

    with patch("llm.AsyncOpenAI") as client_class:
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=response)
        client_class.return_value = client
        await extract_lead(secret_text, correlation_id="corr-llm-123")

    assert "corr-llm-123" in caplog.text
    assert secret_text not in caplog.text


def test_append_lead_logs_correlation_id_not_content(caplog):
    """Sheets-слой пишет correlation_id, но не original_message."""
    caplog.set_level(logging.INFO, logger="sheets")
    client = build_sheets_client()
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = [HEADER]
    client._get_worksheet = MagicMock(return_value=worksheet)
    secret_text = "MY-SECRET-MESSAGE-CONTENT-77"

    client.append_lead(Lead(name="John"), secret_text, correlation_id="corr-sheets-1")

    assert "corr-sheets-1" in caplog.text
    assert secret_text not in caplog.text
