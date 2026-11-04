"""Telegram bot entry point (polling)."""

import asyncio
import logging
import signal

from telegram.ext import Application, CommandHandler, MessageHandler, filters

import handlers
from config import Settings, load_settings
from handlers import handle_text, handle_unsupported, start
from sheets import GoogleSheetsClient, SheetsError

logger = logging.getLogger(__name__)

ALLOWED_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def setup_logging(settings: Settings) -> None:
    """Sets up basic logging."""
    log_level = settings.log_level.upper()
    if log_level not in ALLOWED_LOG_LEVELS:
        raise ValueError(
            f"Invalid LOG_LEVEL: {settings.log_level}. " f"Allowed values are {', '.join(ALLOWED_LOG_LEVELS)}."
        )
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, log_level),
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def build_application(settings: Settings) -> Application:
    """Creates and configures the Application."""
    try:
        client = GoogleSheetsClient(
            credentials_path=settings.google_application_credentials,
            spreadsheet_id=settings.google_spreadsheet_id,
            sheet_name=settings.google_sheet_name,
        )
    except SheetsError as exc:
        logger.warning(
            "Google Sheets unavailable at startup (%s). Bot will start without write capability.",
            type(exc).__name__,
        )
        client = None
    handlers.sheets_client = client
    application = Application.builder().token(settings.telegram_bot_token).build()
    application.bot_data["sheets_client"] = client
    application.bot_data["settings"] = settings
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(
        MessageHandler(
            filters.PHOTO
            | filters.AUDIO
            | filters.VOICE
            | filters.VIDEO
            | filters.Document.ALL
            | filters.Sticker.ALL
            | filters.ANIMATION
            | filters.VIDEO_NOTE
            | filters.CONTACT
            | filters.LOCATION
            | filters.VENUE
            | filters.POLL
            | filters.Dice.ALL,
            handle_unsupported,
        )
    )
    return application


async def main() -> None:
    """Runs the bot with polling and graceful shutdown."""
    settings = load_settings()
    setup_logging(settings)
    application = build_application(settings)

    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _shutdown(signum: int, _frame: object) -> None:
        logger.info("Received shutdown signal %s, shutting down...", signum)
        loop.call_soon_threadsafe(stop_event.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        # signal.signal accepts signal.Signals at runtime; the stub expects int.
        signal.signal(sig, _shutdown)  # type: ignore[arg-type]

    await application.initialize()
    await application.start()
    if application.updater is None:
        raise RuntimeError("Telegram Updater failed to initialize. Check your bot token and network.")
    await application.updater.start_polling()
    logger.info("Bot started (polling).")

    await stop_event.wait()

    await application.updater.stop()
    await application.stop()
    await application.shutdown()
    logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
