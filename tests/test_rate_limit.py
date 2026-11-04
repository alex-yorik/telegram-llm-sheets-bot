"""Тесты in-memory rate limiter и защиты от гонки дедупликации."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import handlers
from handlers import handle_text
from models import Lead


def make_update(
    text: str = "hello",
    message_id: int = 1,
    chat_id: int = 12345,
    user_id: int = 100,
):
    """Создает мок Update с user_id для rate limiter."""
    update = MagicMock()
    message = MagicMock()
    message.text = text
    message.message_id = message_id
    message.reply_text = AsyncMock()
    update.message = message
    update.effective_chat = MagicMock()
    update.effective_chat.id = chat_id
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    return update


def make_context():
    """Создает мок Context с пустым bot_data."""
    context = MagicMock()
    context.bot_data = {}
    return context


def test_rate_limit_allows_three_requests():
    """Первые три запроса пользователя проходят, четвертый блокируется."""
    assert handlers._is_rate_limited(1) is False
    assert handlers._is_rate_limited(1) is False
    assert handlers._is_rate_limited(1) is False
    assert handlers._is_rate_limited(1) is True
    assert len(handlers.request_history[1]) == 3


def test_rate_limit_is_per_user():
    """Лимит одного пользователя не влияет на другого."""
    for _ in range(3):
        assert handlers._is_rate_limited(1) is False

    assert handlers._is_rate_limited(1) is True
    assert handlers._is_rate_limited(2) is False


def test_rate_limit_window_expires(monkeypatch):
    """После окна в 60 секунд старые запросы больше не учитываются."""
    clock = {"now": 100.0}
    monkeypatch.setattr(handlers.time, "monotonic", lambda: clock["now"])

    for _ in range(3):
        assert handlers._is_rate_limited(1) is False
    assert handlers._is_rate_limited(1) is True

    clock["now"] += 61
    assert handlers._is_rate_limited(1) is False


@pytest.mark.asyncio
async def test_handle_text_rate_limit_blocks_llm():
    """После превышения лимита LLM не вызывается, пользователь получает ответ."""
    context = make_context()
    updates = [make_update(message_id=message_id, user_id=555) for message_id in range(1, 5)]

    with patch("handlers.extract_lead", new_callable=AsyncMock) as mock_extract:
        mock_extract.return_value = Lead(name="John")

        for update in updates:
            await handle_text(update, context)

    assert mock_extract.await_count == 3
    assert updates[3].message.reply_text.call_args.args[0] == "Слишком много запросов, подождите минуту"


@pytest.mark.asyncio
async def test_concurrent_duplicate_calls_llm_once():
    """Два одновременных одинаковых update не проходят дедупликацию дважды."""
    context = make_context()
    first_update = make_update(message_id=777, user_id=1)
    second_update = make_update(message_id=777, user_id=1)
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    async def slow_extract(*args, **kwargs):
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return Lead(name="John")

    with patch("handlers.extract_lead", new=slow_extract):
        first = asyncio.create_task(handle_text(first_update, context))
        await started.wait()

        second = asyncio.create_task(handle_text(second_update, context))
        await asyncio.sleep(0.01)

        assert calls == 1

        release.set()
        await asyncio.gather(first, second)

    assert calls == 1
