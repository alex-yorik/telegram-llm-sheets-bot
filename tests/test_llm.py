"""Тесты извлечения данных через LLM (сеть полностью замокана)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from openai import OpenAIError

from llm import LLMRequestError, LLMValidationError, _strip_code_fences, extract_lead


def make_response(content: str | None):
    """Создает мок ответа OpenAI Chat Completions."""
    message = MagicMock()
    message.content = content
    response = MagicMock()
    response.choices = [MagicMock(message=message)]
    return response


@pytest.fixture
def openai_client():
    """Подменяет AsyncOpenAI и возвращает мок клиента."""
    with patch("llm.AsyncOpenAI") as client_class:
        client = AsyncMock()
        client.chat.completions.create = AsyncMock()
        client_class.return_value = client
        yield client


@pytest.mark.asyncio
async def test_extract_lead_valid_json(openai_client):
    """Успешное извлечение валидного JSON."""
    openai_client.chat.completions.create.return_value = make_response('{"name": "John", "phone": "+123"}')

    lead = await extract_lead("John wants to book, phone +123")

    assert lead.name == "John"
    assert lead.phone == "+123"
    assert lead.has_data() is True
    openai_client.chat.completions.create.assert_awaited_once()
    request = openai_client.chat.completions.create.call_args.kwargs
    assert request["messages"][0]["role"] == "system"
    assert request["messages"][1] == {
        "role": "user",
        "content": "John wants to book, phone +123",
    }


@pytest.mark.asyncio
async def test_extract_lead_json_with_code_fences(openai_client):
    """JSON в markdown code fences корректно очищается."""
    openai_client.chat.completions.create.return_value = make_response('```json\n{"name": "John"}\n```')

    lead = await extract_lead("test")

    assert lead.name == "John"


@pytest.mark.asyncio
async def test_extract_lead_invalid_json(openai_client):
    """Невалидный JSON дает LLMValidationError."""
    openai_client.chat.completions.create.return_value = make_response("not valid json")

    with pytest.raises(LLMValidationError):
        await extract_lead("test")


@pytest.mark.asyncio
async def test_extract_lead_empty_choices(openai_client):
    """Пустой список choices не может быть провалидирован."""
    response = MagicMock()
    response.choices = []
    openai_client.chat.completions.create.return_value = response

    with pytest.raises(LLMValidationError):
        await extract_lead("test")


@pytest.mark.asyncio
async def test_extract_lead_none_content(openai_client):
    """None вместо контента считается ошибкой валидации."""
    openai_client.chat.completions.create.return_value = make_response(None)

    with pytest.raises(LLMValidationError):
        await extract_lead("test")


@pytest.mark.asyncio
async def test_extract_lead_wrong_field_type(openai_client):
    """Неверный тип поля отклоняется Pydantic."""
    openai_client.chat.completions.create.return_value = make_response('{"name": {"unexpected": "object"}}')

    with pytest.raises(LLMValidationError):
        await extract_lead("test")


@pytest.mark.asyncio
async def test_extract_lead_openai_error(openai_client):
    """Ошибка SDK преобразуется в LLMRequestError."""
    openai_client.chat.completions.create.side_effect = OpenAIError("API Error")

    with pytest.raises(LLMRequestError):
        await extract_lead("test")


@pytest.mark.asyncio
async def test_extract_lead_unexpected_error(openai_client):
    """Неожиданная ошибка также становится LLMRequestError."""
    openai_client.chat.completions.create.side_effect = RuntimeError("boom")

    with pytest.raises(LLMRequestError):
        await extract_lead("test")


@pytest.mark.asyncio
async def test_extract_lead_all_fields_null(openai_client):
    """Ответ со всеми null валиден, но не содержит данных."""
    openai_client.chat.completions.create.return_value = make_response(
        '{"name": null, "phone": null, "service": null, "date": null, "time": null}'
    )

    lead = await extract_lead("test")

    assert lead.has_data() is False


def test_strip_code_fences_without_language():
    """Fences без указания языка тоже удаляются."""
    assert _strip_code_fences('```\n{"name": "John"}\n```') == '{"name": "John"}'


def test_strip_code_fences_plain_text():
    """Текст без fences возвращается без изменений."""
    assert _strip_code_fences('{"name": "John"}') == '{"name": "John"}'


def test_strip_code_fences_surrounding_whitespace():
    """Лишние пробелы вокруг значения удаляются."""
    assert _strip_code_fences("  test  ") == "test"
