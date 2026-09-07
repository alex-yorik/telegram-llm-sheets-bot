"""Точка входа Telegram-бота (polling)."""

import asyncio
import logging
import signal

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import settings
import handlers
from handlers import handle_text, start
from sheets import GoogleSheetsClient, SheetsError

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Настраивает базовое логирование."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
    )


def build_application() -> Application:
    """Создает и настраивает Application."""
    try:
        client = GoogleSheetsClient()
    except SheetsError:
        logger.exception("Sheets недоступны, бот стартует без записи")
        client = None
    handlers.sheets_client = client
    application = (
        Application.builder().token(settings.telegram_bot_token).build()
    )
    application.bot_data["sheets_client"] = client
    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )
    return application


async def main() -> None:
    """Запускает бота с polling и корректным завершением."""
    setup_logging()
    application = build_application()

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown(signum: int, _frame: object) -> None:
        logger.info("Получен сигнал %s, завершаем работу...", signum)
        loop.call_soon_threadsafe(stop_event.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _shutdown)  # type: ignore[arg-type]

    await application.initialize()
    await application.start()
    assert application.updater is not None
    await application.updater.start_polling()
    logger.info("Бот запущен (polling).")

    await stop_event.wait()

    await application.updater.stop()
    await application.stop()
    await application.shutdown()
    logger.info("Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())
