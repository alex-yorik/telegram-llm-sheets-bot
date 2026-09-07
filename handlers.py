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

# Устанавливается в main.py при старте (дублируется в bot_data).
sheets_client: "GoogleSheetsClient | None" = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start."""
    if update.message is None:
        return
    await update.message.reply_text(
        "Hi! Send me a text message and I'll save the details to the spreadsheet."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Извлекает данные заявки из текста через LLM."""
    if update.message is None or update.message.text is None:
        return
    chat_id = update.effective_chat.id if update.effective_chat else None
    text = update.message.text
    logger.info("Received message from chat_id=%s: %s", chat_id, text)
    logger.info("Calling extract_lead for chat_id=%s", chat_id)
    try:
        lead = await extract_lead(text)
    except LLMValidationError:
        await update.message.reply_text(
            "Could not extract data, please send more details"
        )
        return
    except LLMRequestError:
        await update.message.reply_text("Processing error, try again later")
        return
    except Exception:
        logger.exception("Failed to process message chat_id=%s", chat_id)
        await update.message.reply_text("An error occurred")
        return
    client = sheets_client or context.bot_data.get("sheets_client")
    saved = False
    if client is None:
        logger.warning("SheetsClient not initialized, skipping write")
    else:
        try:
            await asyncio.to_thread(client.append_lead, lead, text)
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
    await update.message.reply_text(answer)
