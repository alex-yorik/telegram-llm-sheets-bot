"""Обработчики команд и сообщений Telegram-бота."""

import asyncio
import logging
from typing import TYPE_CHECKING

from telegram import Update
from telegram.ext import ContextTypes

from llm import LLMRequestError, LLMValidationError, extract_lead
from sheets import SheetsError

if TYPE_CHECKING:
    from sheets import GoogleSheetsClient

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000
MAX_PROCESSED_MESSAGES = 1000

# Устанавливается в main.py при старте (дублируется в bot_data).
sheets_client: "GoogleSheetsClient | None" = None

# Ключ (chat_id, message_id): message_id уникален только внутри чата.
processed_messages: set[tuple[int | None, int]] = set()


async def handle_unsupported(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Отвечает на сообщения неподдерживаемых типов."""
    if update.message is None:
        return
    await update.message.reply_text(
        "I only process text messages. Please send me a text description."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    if update.message is None:
        return
    await update.message.reply_text(
        "Hi! Send me a text message and I'll save the details to the spreadsheet.\n\n"
        "Note: Your messages are processed by an external LLM API and extracted "
        "data may be saved to Google Sheets."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Извлекает данные заявки из текста через LLM."""
    if update.message is None or update.message.text is None:
        return
    chat_id = update.effective_chat.id if update.effective_chat else None
    text = update.message.text
    message_id = update.message.message_id

    message_key = (chat_id, message_id)
    if message_key in processed_messages:
        logger.info(
            "Duplicate message_id=%s from chat_id=%s, skipping",
            message_id,
            chat_id,
        )
        return
    processed_messages.add(message_key)
    if len(processed_messages) > MAX_PROCESSED_MESSAGES:
        processed_messages.clear()

    if len(text) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text(
            f"Message is too long (max {MAX_MESSAGE_LENGTH} characters). "
            f"Please send a shorter message."
        )
        logger.warning(
            "Message too long from chat_id=%s, length=%s", chat_id, len(text)
        )
        return

    logger.info("Received message from chat_id=%s, length=%s", chat_id, len(text))
    logger.info("Calling extract_lead for chat_id=%s", chat_id)
    try:
        lead = await extract_lead(text)
    except LLMValidationError:
        await update.message.reply_text(
            "Could not extract data. Please send a message with more details "
            "(name, phone, service, etc.)."
        )
        return
    except LLMRequestError:
        await update.message.reply_text("Processing error, try again later")
        return
    except Exception:
        logger.exception("Failed to process message chat_id=%s", chat_id)
        await update.message.reply_text("An error occurred")
        return

    if not lead.has_data():
        logger.warning("Empty lead from chat_id=%s", chat_id)
        await update.message.reply_text(
            "Could not extract meaningful data. Please send a message with more "
            "details (name, phone, service, etc.)."
        )
        return

    client = sheets_client or context.bot_data.get("sheets_client")
    saved = False
    if client is None:
        logger.warning("SheetsClient not initialized, skipping write")
    else:
        try:
            await asyncio.to_thread(client.append_lead, lead, text, chat_id)
            saved = True
        except SheetsError:
            logger.exception(
                "Failed to save lead to spreadsheet chat_id=%s", chat_id
            )
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
        answer += (
            "\n⚠️ Data extracted but could not be saved to spreadsheet. "
            "Please try again later."
        )
    await update.message.reply_text(answer)
