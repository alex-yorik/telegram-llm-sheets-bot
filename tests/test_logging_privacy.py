"""Тесты приватности логирования: реальные Telegram ID и текст не попадают в логи."""

import logging
import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import handlers
import main
from handlers import handle_text
from llm import LLMRequestError, LLMValidationError, extract_lead
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
async def test_extract_lead_logs_correlation_id_not_content(caplog, test_settings):
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
        await extract_lead(secret_text, correlation_id="corr-llm-123", settings=test_settings)

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


def test_sheets_initialization_does_not_log_spreadsheet_id_or_credentials_path(caplog):
    """Инициализация Sheets не пишет spreadsheet_id и путь к credentials."""
    caplog.set_level(logging.INFO, logger="sheets")
    secret_spreadsheet = "secret-spreadsheet-id-123"
    secret_credentials = "/tmp/secret-service-account.json"

    with (
        patch("sheets.Credentials.from_service_account_file"),
        patch("sheets.gspread.authorize"),
    ):
        GoogleSheetsClient(
            credentials_path=secret_credentials,
            spreadsheet_id=secret_spreadsheet,
            sheet_name="Sheet1",
        )

    assert "GoogleSheetsClient initialized" in caplog.text
    assert secret_spreadsheet not in caplog.text
    assert secret_credentials not in caplog.text


def test_sheets_init_error_does_not_log_credentials_path_or_traceback(caplog):
    """Ошибка credentials не раскрывает путь к файлу и не печатает traceback."""
    caplog.set_level(logging.INFO, logger="sheets")
    secret_credentials = "/tmp/secret-service-account.json"

    with (
        patch(
            "sheets.Credentials.from_service_account_file",
            side_effect=OSError(f"cannot read {secret_credentials}"),
        ),
        pytest.raises(SheetsError),
    ):
        GoogleSheetsClient(
            credentials_path=secret_credentials,
            spreadsheet_id="secret-spreadsheet-id-123",
        )

    assert "Failed to initialize GoogleSheetsClient (OSError)" in caplog.text
    assert secret_credentials not in caplog.text
    assert "Traceback" not in caplog.text


def test_sheets_open_error_does_not_log_spreadsheet_id(caplog):
    """Ошибка открытия таблицы не пишет spreadsheet_id и не печатает traceback."""
    caplog.set_level(logging.INFO, logger="sheets")
    secret_spreadsheet = "secret-spreadsheet-id-123"
    client = build_sheets_client()
    client._client.open_by_key.side_effect = RuntimeError(f"cannot open {secret_spreadsheet}")

    with pytest.raises(SheetsError):
        client._get_worksheet()

    assert secret_spreadsheet not in caplog.text
    assert "Traceback" not in caplog.text


def test_sheets_save_error_does_not_log_content_or_spreadsheet_id(caplog):
    """Ошибка записи не раскрывает текст заявки, spreadsheet_id и traceback."""
    caplog.set_level(logging.INFO, logger="sheets")
    secret_text = "MY-SECRET-MESSAGE-CONTENT-88"
    client = build_sheets_client()
    worksheet = MagicMock()
    worksheet.get_all_values.side_effect = RuntimeError(f"write failed for {secret_text} in test-spreadsheet-id")
    client._get_worksheet = MagicMock(return_value=worksheet)

    with pytest.raises(SheetsError):
        client.append_lead(Lead(name="John"), secret_text, correlation_id="corr-sheets-2")

    assert secret_text not in caplog.text
    assert "test-spreadsheet-id" not in caplog.text
    assert "Traceback" not in caplog.text


def test_main_startup_failure_does_not_log_credentials_path(caplog, test_settings):
    """Недоступные credentials при старте не пишут путь к файлу в логи."""
    caplog.set_level(logging.INFO, logger="main")
    secret_credentials = "/tmp/secret-service-account.json"
    application = MagicMock()
    builder = MagicMock()
    builder.token.return_value.build.return_value = application

    with (
        patch("main.GoogleSheetsClient", side_effect=SheetsError(f"cannot read {secret_credentials}")),
        patch("main.Application.builder", return_value=builder),
    ):
        main.build_application(test_settings)

    assert secret_credentials not in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.asyncio
async def test_handler_exception_does_not_log_content_or_traceback(caplog):
    """Неожиданное исключение не печатает traceback с текстом сообщения."""
    caplog.set_level(logging.INFO, logger="handlers")
    secret_text = "MY-SECRET-EXCEPTION-CONTENT-42"

    with patch(
        "handlers.extract_lead",
        new_callable=AsyncMock,
        side_effect=RuntimeError(secret_text),
    ):
        await handle_text(make_update(), make_context())

    assert secret_text not in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.asyncio
async def test_llm_validation_error_does_not_log_content_or_traceback(caplog, test_settings):
    """Невалидный ответ LLM не печатает traceback с исходным содержимым."""
    caplog.set_level(logging.INFO, logger="llm")
    secret_text = "MY-SECRET-VALIDATION-CONTENT-55"
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=secret_text))]

    with patch("llm.AsyncOpenAI") as client_class:
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(return_value=response)
        client_class.return_value = client
        with pytest.raises(LLMValidationError):
            await extract_lead(secret_text, correlation_id="corr-bad-json", settings=test_settings)

    assert "corr-bad-json" in caplog.text
    assert secret_text not in caplog.text
    assert "Traceback" not in caplog.text


@pytest.mark.asyncio
async def test_llm_request_error_does_not_log_api_key_or_content(caplog, test_settings):
    """Ошибка LLM-запроса не раскрывает API-ключ и текст сообщения."""
    caplog.set_level(logging.INFO, logger="llm")
    secret_text = "MY-SECRET-LLM-CONTENT-66"
    secret_key = "test-llm-key"

    with patch("llm.AsyncOpenAI") as client_class:
        client = AsyncMock()
        client.chat.completions.create = AsyncMock(
            side_effect=RuntimeError(f"auth failed for {secret_key} text={secret_text}")
        )
        client_class.return_value = client
        with pytest.raises(LLMRequestError):
            await extract_lead(secret_text, correlation_id="corr-llm-fail", settings=test_settings)

    assert secret_key not in caplog.text
    assert secret_text not in caplog.text
    assert "Traceback" not in caplog.text
