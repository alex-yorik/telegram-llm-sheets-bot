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
        "Привет! Отправь мне текстовое сообщение..."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Извлекает данные заявки из текста через LLM."""
    if update.message is None or update.message.text is None:
        return
    chat_id = update.effective_chat.id if update.effective_chat else None
    text = update.message.text
    logger.info("Получено сообщение от chat_id=%s: %s", chat_id, text)
    logger.info("Вызываю extract_lead для chat_id=%s", chat_id)
    try:
        lead = await extract_lead(text)
    except LLMValidationError:
        await update.message.reply_text(
            "Не удалось извлечь данные, отправь подробнее"
        )
        return
    except LLMRequestError:
        await update.message.reply_text("Ошибка обработки, попробуй позже")
        return
    except Exception:
        logger.exception("Ошибка обработки сообщения chat_id=%s", chat_id)
        await update.message.reply_text("Произошла ошибка")
        return
    client = sheets_client or context.bot_data.get("sheets_client")
    saved = False
    if client is None:
        logger.warning("SheetsClient не инициализирован, пропускаю запись")
    else:
        try:
            await asyncio.to_thread(client.append_lead, lead, text)
            saved = True
        except SheetsError:
            logger.exception(
                "Не удалось сохранить лида в таблицу chat_id=%s", chat_id
            )
    answer = (
        f"Извлечённые данные:\n"
        f"Имя: {lead.name or '-'}\n"
        f"Телефон: {lead.phone or '-'}\n"
        f"Услуга: {lead.service or '-'}\n"
        f"Дата: {lead.date or '-'}\n"
        f"Время: {lead.time or '-'}"
    )
    if saved:
        answer += "\n✅ Данные сохранены в таблицу"
    await update.message.reply_text(answer)
