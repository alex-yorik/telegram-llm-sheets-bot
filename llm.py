"""Извлечение данных заявки из текста через LLM."""

import json
import logging
import re

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from config import settings
from models import Lead

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Ты извлекаешь данные заявки из текста пользователя. "
    "Верни ТОЛЬКО валидный JSON без пояснений и без markdown-обёртки. "
    "Формат: {\"name\": str | null, \"phone\": str | null, "
    "\"service\": str | null, \"date\": str | null, \"time\": str | null}. "
    "Если поле не найдено в тексте, укажи null. "
    "Дату и время верни как в тексте, без переформатирования."
)


class LLMRequestError(Exception):
    """Ошибка запроса к LLM (сеть, API, таймаут)."""


class LLMValidationError(Exception):
    """LLM вернул данные, которые не удалось распарсить/валидировать."""


def _strip_code_fences(content: str) -> str:
    """Убирает markdown code fences из ответа LLM."""
    text = content.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


async def extract_lead(text: str) -> Lead:
    """Извлекает данные заявки из текста через LLM."""
    logger.info(
        "LLM request: base_url=%s model=%s text=%.100s",
        settings.llm_api_base,
        settings.llm_model,
        text,
    )
    client = AsyncOpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_api_base,
        timeout=settings.llm_timeout_seconds,
    )
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        logger.info("LLM response received: %s", response)
    except OpenAIError as exc:
        logger.exception("LLM request failed")
        raise LLMRequestError(str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error during LLM request")
        raise LLMRequestError(str(exc)) from exc

    try:
        content = (response.choices[0].message.content or "").strip()
        logger.info("LLM raw content: %s", content)
        cleaned = _strip_code_fences(content)
        data = json.loads(cleaned)
        return Lead.model_validate(data)
    except (json.JSONDecodeError, ValidationError, IndexError) as exc:
        logger.exception("Failed to validate LLM response")
        raise LLMValidationError(str(exc)) from exc
