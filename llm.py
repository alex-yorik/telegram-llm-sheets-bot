"""Extract lead data from text via LLM."""

import json
import logging
import re

from openai import AsyncOpenAI, OpenAIError
from openai.types.chat import ChatCompletion
from pydantic import ValidationError

from config import Settings, load_settings
from models import Lead

logger = logging.getLogger(__name__)

# Reused across requests to avoid creating a new client (and connection pool) per call.
_client: AsyncOpenAI | None = None
_client_signature: tuple[str, str, int] | None = None

SYSTEM_PROMPT = (
    "Ты извлекаешь данные заявки из текста пользователя. "
    "Верни ТОЛЬКО валидный JSON без пояснений и без markdown-обёртки. "
    'Формат: {"name": str | null, "phone": str | null, '
    '"service": str | null, "date": str | null, "time": str | null}. '
    "Если поле не найдено в тексте, укажи null. "
    "Дату и время верни как в тексте, без переформатирования."
)


class LLMRequestError(Exception):
    """LLM request error (network, API, timeout)."""


class LLMValidationError(Exception):
    """The LLM returned data that could not be parsed/validated."""


def _get_client(settings: Settings) -> AsyncOpenAI:
    """Returns the shared AsyncOpenAI client, creating it once per configuration."""
    global _client, _client_signature
    signature = (settings.llm_api_key, settings.llm_api_base, settings.llm_timeout_seconds)
    if _client is None or _client_signature != signature:
        _client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_base,
            timeout=settings.llm_timeout_seconds,
        )
        _client_signature = signature
        logger.info("OpenAI client initialized (base_url=%s)", settings.llm_api_base)
    return _client


def _strip_code_fences(content: str) -> str:
    """Strips markdown code fences from the LLM response."""
    text = content.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def _parse_lead_response(
    response: ChatCompletion,
    correlation_id: str | None,
) -> Lead:
    """Validates the LLM response and maps failures to LLMValidationError."""
    try:
        content = (response.choices[0].message.content or "").strip()
        cleaned = _strip_code_fences(content)
        data = json.loads(cleaned)
        return Lead.model_validate(data)
    except (json.JSONDecodeError, ValidationError, IndexError) as exc:
        logger.error(
            "Failed to validate LLM response (correlation_id=%s, error=%s)",
            correlation_id,
            type(exc).__name__,
        )
        raise LLMValidationError(str(exc)) from exc


async def extract_lead(
    text: str,
    correlation_id: str | None = None,
    settings: Settings | None = None,
) -> Lead:
    """Extracts lead data from the text via LLM."""
    if settings is None:
        settings = load_settings()
    logger.info(
        "LLM request sent (correlation_id=%s, base_url=%s, model=%s, length=%s)",
        correlation_id,
        settings.llm_api_base,
        settings.llm_model,
        len(text),
    )
    client = _get_client(settings)
    try:
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        logger.info("LLM response received (correlation_id=%s)", correlation_id)
    except OpenAIError as exc:
        logger.error("LLM request failed (correlation_id=%s, error=%s)", correlation_id, type(exc).__name__)
        raise LLMRequestError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Unexpected error during LLM request (correlation_id=%s, error=%s)",
            correlation_id,
            type(exc).__name__,
        )
        raise LLMRequestError(str(exc)) from exc

    return _parse_lead_response(response, correlation_id)
