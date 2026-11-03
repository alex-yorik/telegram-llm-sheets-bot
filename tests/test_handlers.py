"""Тесты обработчиков Telegram (LLM и Sheets замоканы)."""

from collections import deque
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest

import handlers
from handlers import handle_text, handle_unsupported, start
from llm import LLMRequestError, LLMValidationError
from models import Lead
from sheets import SheetsError


def make_update(
    text: str = "hello",
    message_id: int = 1,
    chat_id: int | None = 12345,
    with_message: bool = True,
    with_chat: bool = True,
):
    """Создает мок Update для тестирования."""
    update = MagicMock()
    if not with_message:
        update.message = None
        return update
    message = MagicMock()
    message.text = text
    message.message_id = message_id
    message.reply_text = AsyncMock()
    update.message = message
    if with_chat:
        update.effective_chat = MagicMock()
        update.effective_chat.id = chat_id
    else:
        update.effective_chat = None
    return update


def make_context(client=None):
    """Создает мок Context с bot_data."""
    context = MagicMock()
    context.bot_data = {}
    if client is not None:
        context.bot_data["sheets_client"] = client
    return context


@pytest.mark.asyncio
async def test_start_handler():
    """Приветствие содержит уведомление об обработке данных."""
    update = make_update("")

    await start(update, make_context())

    update.message.reply_text.assert_awaited_once()
    text = update.message.reply_text.call_args.args[0]
    assert "Note:" in text


@pytest.mark.asyncio
async def test_start_without_message():
    """Без message обработчик молча выходит."""
    update = make_update(with_message=False)

    await start(update, make_context())


@pytest.mark.asyncio
async def test_unsupported_message():
    """Неподдерживаемый тип получает пояснение."""
    update = make_update()

    await handle_unsupported(update, make_context())

    update.message.reply_text.assert_awaited_once()
    assert "only process text" in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_unsupported_without_message():
    """Без message обработчик молча выходит."""
    update = make_update(with_message=False)

    await handle_unsupported(update, make_context())


@pytest.mark.asyncio
async def test_handle_text_success():
    """Успешная обработка сохраняет заявку в Sheets."""
    update = make_update("John wants to book, phone +123")
    client = MagicMock()
    context = make_context(client)
    lead = Lead(name="John", phone="+123")

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = lead

        await handle_text(update, context)

    mock_extract.assert_awaited_once_with("John wants to book, phone +123", correlation_id=ANY)
    client.append_lead.assert_called_once_with(lead, "John wants to book, phone +123", ANY)
    text = update.message.reply_text.call_args.args[0]
    assert "Data saved to spreadsheet" in text


@pytest.mark.asyncio
async def test_handle_text_uses_bot_data_client():
    """Клиент из context.bot_data используется как fallback."""
    update = make_update()
    client = MagicMock()
    context = make_context(client)

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        await handle_text(update, context)

    client.append_lead.assert_called_once()


@pytest.mark.asyncio
async def test_handle_text_without_sheets_client():
    """Без клиента Sheets данные показываются, но не сохраняются."""
    update = make_update()

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        await handle_text(update, make_context())

    text = update.message.reply_text.call_args.args[0]
    assert "could not be saved to spreadsheet" in text


@pytest.mark.asyncio
async def test_handle_text_sheets_error():
    """Ошибка Sheets не теряет извлеченные данные."""
    update = make_update()
    client = MagicMock()
    client.append_lead.side_effect = SheetsError("Sheets Error")

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        await handle_text(update, make_context(client))

    text = update.message.reply_text.call_args.args[0]
    assert "could not be saved to spreadsheet" in text


@pytest.mark.asyncio
async def test_handle_text_llm_error():
    """Ошибка запроса к LLM обрабатывается ответом пользователю."""
    update = make_update()

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = LLMRequestError("API Error")

        await handle_text(update, make_context())

    assert "Processing error" in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_handle_text_validation_error():
    """Ошибка валидации LLM просит больше деталей."""
    update = make_update()

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = LLMValidationError("Invalid data")

        await handle_text(update, make_context())

    assert "Could not extract data" in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_handle_text_unexpected_error():
    """Неожиданное исключение не роняет обработчик."""
    update = make_update()

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = RuntimeError("boom")

        await handle_text(update, make_context())

    assert "An error occurred" in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_handle_text_empty_lead():
    """Пустая заявка просит больше деталей."""
    update = make_update()

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead()

        await handle_text(update, make_context())

    assert "Could not extract meaningful data" in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_handle_text_without_message():
    """Без message обработчик молча выходит."""
    update = make_update(with_message=False)

    await handle_text(update, make_context())


@pytest.mark.asyncio
async def test_handle_text_without_text():
    """Без текста обработчик молча выходит."""
    update = make_update()
    update.message.text = None

    await handle_text(update, make_context())


@pytest.mark.asyncio
async def test_handle_text_too_long(monkeypatch):
    """Слишком длинное сообщение отклоняется до вызова LLM."""
    monkeypatch.setattr(handlers, "MAX_MESSAGE_LENGTH", 10)
    update = make_update("a" * 11)

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        await handle_text(update, make_context())

    mock_extract.assert_not_awaited()
    assert "too long" in update.message.reply_text.call_args.args[0]


@pytest.mark.asyncio
async def test_handle_text_duplicate_message():
    """Повторная доставка одного update не создаёт дубль."""
    client = MagicMock()
    context = make_context(client)

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        await handle_text(make_update(message_id=999), context)
        await handle_text(make_update(message_id=999), context)

    mock_extract.assert_awaited_once()
    client.append_lead.assert_called_once()


@pytest.mark.asyncio
async def test_handle_text_same_message_id_in_different_chats():
    """Одинаковый message_id в разных чатах не считается дублем."""
    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        await handle_text(make_update(message_id=1, chat_id=111), make_context())
        await handle_text(make_update(message_id=1, chat_id=222), make_context())

    assert mock_extract.await_count == 2


@pytest.mark.asyncio
async def test_handle_text_processed_cache_respects_limit(monkeypatch):
    """Кэш не превышает MAX_PROCESSED_MESSAGES записей."""
    monkeypatch.setattr(handlers, "processed_messages", deque(maxlen=3))
    client = MagicMock()
    context = make_context(client)

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        for message_id in range(1, 6):
            await handle_text(make_update(message_id=message_id), context)

    assert len(handlers.processed_messages) == 3
    assert mock_extract.await_count == 5


@pytest.mark.asyncio
async def test_handle_text_processed_cache_evicts_oldest_only(monkeypatch):
    """При переполнении удаляются только старейшие записи, новые сохраняются."""
    monkeypatch.setattr(handlers, "processed_messages", deque(maxlen=3))
    client = MagicMock()
    context = make_context(client)

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        for message_id in range(1, 5):
            await handle_text(make_update(message_id=message_id), context)

    assert list(handlers.processed_messages) == [(12345, 2), (12345, 3), (12345, 4)]
    assert (12345, 1) not in handlers.processed_messages


@pytest.mark.asyncio
async def test_handle_text_retry_after_llm_error():
    """После временной ошибки LLM повторная попытка возможна."""
    client = MagicMock()
    context = make_context(client)

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.side_effect = [LLMRequestError("API Error"), Lead(name="John")]

        await handle_text(make_update(message_id=42), context)
        await handle_text(make_update(message_id=42), context)

    assert mock_extract.await_count == 2
    client.append_lead.assert_called_once()


@pytest.mark.asyncio
async def test_handle_text_retry_after_sheets_error():
    """После временной ошибки Sheets повторная попытка возможна."""
    client = MagicMock()
    client.append_lead.side_effect = [SheetsError("Sheets Error"), None]
    context = make_context(client)

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        await handle_text(make_update(message_id=43), context)
        await handle_text(make_update(message_id=43), context)

    assert mock_extract.await_count == 2
    assert client.append_lead.call_count == 2


@pytest.mark.asyncio
async def test_handle_text_success_not_reprocessed():
    """Успешно завершённое сообщение не обрабатывается повторно."""
    client = MagicMock()
    context = make_context(client)

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        await handle_text(make_update(message_id=44), context)
        await handle_text(make_update(message_id=44), context)

    mock_extract.assert_awaited_once()
    client.append_lead.assert_called_once()


@pytest.mark.asyncio
async def test_handle_text_without_chat():
    """Без effective_chat chat_id равен None."""
    update = make_update(with_chat=False)
    client = MagicMock()

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        await handle_text(update, make_context(client))

    client.append_lead.assert_called_once_with(mock_extract.return_value, "hello", ANY)
