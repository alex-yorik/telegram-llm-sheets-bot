"""Обработчики команд и сообщений Telegram-бота."""

import asyncio
import logging
import uuid
from collections import deque
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import ContextTypes

from llm import LLMRequestError, LLMValidationError, extract_lead
from models import Lead
from sheets import SheetsError

if TYPE_CHECKING:
    from sheets import GoogleSheetsClient

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000
MAX_PROCESSED_MESSAGES = 1000

# Устанавливается в main.py при старте (дублируется в bot_data).
sheets_client: "GoogleSheetsClient | None" = None

# Ключ (chat_id, message_id): message_id уникален только внутри чата.
# deque(maxlen=N) хранит только последние N записей и сам вытесняет старейшие.
processed_messages: deque[tuple[int | None, int]] = deque(maxlen=MAX_PROCESSED_MESSAGES)


async def handle_unsupported(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отвечает на сообщения неподдерживаемых типов."""
    if update.message is None:
        return
    await update.message.reply_text("I only process text messages. Please send me a text description.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    if update.message is None:
        return
    await update.message.reply_text(
        "Hi! Send me a text message and I'll save the details to the spreadsheet.\n\n"
        "Note: Your messages are processed by an external LLM API and extracted "
        "data may be saved to Google Sheets."
    )


def _is_duplicate(chat_id: int | None, message_id: int, correlation_id: str) -> bool:
    """Проверяет, обрабатывалось ли сообщение ранее."""
    if (chat_id, message_id) in processed_messages:
        logger.info(
            "Duplicate message received (correlation_id=%s, message_id=%s), skipping",
            correlation_id,
            message_id,
        )
        return True
    return False


def _mark_seen(chat_id: int | None, message_id: int) -> None:
    """Регистрирует успешно обработанное сообщение (FIFO-вытеснение)."""
    processed_messages.append((chat_id, message_id))


async def _reject_long_message(update: Update, text: str, correlation_id: str) -> bool:
    """Отвечает отказом, если текст превышает лимит."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        return False
    await update.message.reply_text(
        f"Message is too long (max {MAX_MESSAGE_LENGTH} characters). " "Please send a shorter message."
    )
    logger.warning("Message too long (correlation_id=%s, length=%s)", correlation_id, len(text))
    return True


async def _extract_or_reply(update: Update, text: str, correlation_id: str) -> Lead | None:
    """Извлекает заявку или отвечает пользователю об ошибке."""
    logger.info("Received message (correlation_id=%s, length=%s)", correlation_id, len(text))
    logger.info("Calling extract_lead (correlation_id=%s)", correlation_id)
    try:
        lead = await extract_lead(text, correlation_id=correlation_id)
    except LLMValidationError:
        await update.message.reply_text(
            "Could not extract data. Please send a message with more details " "(name, phone, service, etc.)."
        )
        return None
    except LLMRequestError:
        await update.message.reply_text("Processing error, try again later")
        return None
    except Exception:
        logger.exception("Failed to process message (correlation_id=%s)", correlation_id)
        await update.message.reply_text("An error occurred")
        return None

    if not lead.has_data():
        logger.warning("Empty lead (correlation_id=%s)", correlation_id)
        await update.message.reply_text(
            "Could not extract meaningful data. Please send a message with more "
            "details (name, phone, service, etc.)."
        )
        return None
    return lead


async def _save_lead(
    lead: Lead,
    original_message: str,
    correlation_id: str,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """Сохраняет заявку в Google Sheets, возвращает признак успеха."""
    client = sheets_client or context.bot_data.get("sheets_client")
    if client is None:
        logger.warning("SheetsClient not initialized, skipping write (correlation_id=%s)", correlation_id)
        return False
    try:
        await asyncio.to_thread(client.append_lead, lead, original_message, correlation_id)
        return True
    except SheetsError:
        logger.exception("Failed to save lead to spreadsheet (correlation_id=%s)", correlation_id)
        return False


def _format_answer(lead: Lead, saved: bool) -> str:
    """Формирует ответ пользователю с извлеченными данными."""
    answer = (
        f"Extracted data:\n"
        f"Name: {lead.name or '-'}\n"
        f"Phone: {lead.phone or '-'}\n"
        f"Service: {lead.service or '-'}\n"
        f"Date: {lead.date or '-'}\n"
        f"Time: {lead.time or '-'}"
    )
    if saved:
        answer += "\n✅ Data saved to spreadsheet"
    else:
        answer += "\n⚠️ Data extracted but could not be saved to spreadsheet. " "Please try again later."
    return answer


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Извлекает данные заявки из текста через LLM."""
    if update.message is None or update.message.text is None:
        return
    chat_id = update.effective_chat.id if update.effective_chat else None
    text = update.message.text
    message_id = update.message.message_id
    correlation_id = str(uuid.uuid4())

    if _is_duplicate(chat_id, message_id, correlation_id):
        return
    if await _reject_long_message(update, text, correlation_id):
        return

    lead = await _extract_or_reply(update, text, correlation_id)
    if lead is None:
        return

    saved = await _save_lead(lead, text, correlation_id, context)
    if saved:
        _mark_seen(chat_id, message_id)
    await update.message.reply_text(_format_answer(lead, saved))
