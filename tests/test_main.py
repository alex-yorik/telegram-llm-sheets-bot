"""Тесты сборки и запуска приложения."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

import handlers
import main
from sheets import SheetsError

REQUIRED_ENV = (
    "TELEGRAM_BOT_TOKEN",
    "LLM_API_KEY",
    "GOOGLE_SPREADSHEET_ID",
    "GOOGLE_APPLICATION_CREDENTIALS",
)


def make_builder():
    """Создает мок цепочки Application.builder().token(...).build()."""
    application = MagicMock()
    builder = MagicMock()
    builder.token.return_value.build.return_value = application
    return application, builder


def test_setup_logging(test_settings):
    """Логирование настраивается один раз и глушит httpx."""
    with (
        patch("main.logging.basicConfig") as basic_config,
        patch("main.logging.getLogger") as get_logger,
    ):
        main.setup_logging(test_settings)

    basic_config.assert_called_once()
    assert get_logger.call_count == 2


def test_setup_logging_applies_valid_level(test_settings):
    """Допустимый LOG_LEVEL передается в logging без отката."""
    debug_settings = test_settings.model_copy(update={"log_level": "debug"})
    with (
        patch("main.logging.basicConfig") as basic_config,
        patch("main.logging.getLogger"),
    ):
        main.setup_logging(debug_settings)

    assert basic_config.call_args.kwargs["level"] == logging.DEBUG


def test_setup_logging_rejects_invalid_level(test_settings):
    """Неверный LOG_LEVEL останавливает запуск с ValueError."""
    invalid_settings = test_settings.model_copy(update={"log_level": "TRACE"})
    with pytest.raises(ValueError, match="Invalid LOG_LEVEL: TRACE"):
        main.setup_logging(invalid_settings)


def test_build_application_registers_handlers(test_settings):
    """Приложение получает три обработчика и клиент Sheets."""
    application, builder = make_builder()
    with (
        patch("main.GoogleSheetsClient") as sheets_class,
        patch("main.Application.builder", return_value=builder),
    ):
        result = main.build_application(test_settings)

    assert result is application
    assert application.add_handler.call_count == 3
    assert handlers.sheets_client is sheets_class.return_value
    application.bot_data.__setitem__.assert_any_call("sheets_client", sheets_class.return_value)
    application.bot_data.__setitem__.assert_any_call("settings", test_settings)


def test_build_application_without_sheets(test_settings):
    """При недоступном Sheets бот стартует без записи."""
    application, builder = make_builder()
    with (
        patch("main.GoogleSheetsClient", side_effect=SheetsError("no credentials")),
        patch("main.Application.builder", return_value=builder),
    ):
        result = main.build_application(test_settings)

    assert result is application
    assert handlers.sheets_client is None
    application.bot_data.__setitem__.assert_any_call("sheets_client", None)


@pytest.mark.asyncio
async def test_main_fails_without_required_config(monkeypatch, tmp_path):
    """Запуск останавливается, если обязательные переменные не заданы."""
    monkeypatch.chdir(tmp_path)
    for name in REQUIRED_ENV:
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValidationError):
        await main.main()


@pytest.mark.asyncio
async def test_main_starts_and_stops(test_settings):
    """main() запускает polling и корректно завершается."""
    application = MagicMock()
    application.initialize = AsyncMock()
    application.start = AsyncMock()
    application.stop = AsyncMock()
    application.shutdown = AsyncMock()
    application.updater = MagicMock()
    application.updater.start_polling = AsyncMock()
    application.updater.stop = AsyncMock()
    loop = MagicMock()
    stop_event = MagicMock()
    stop_event.wait = AsyncMock()

    with (
        patch("main.load_settings", return_value=test_settings),
        patch("main.setup_logging"),
        patch("main.build_application", return_value=application),
        patch("main.asyncio.get_running_loop", return_value=loop),
        patch("main.asyncio.Event", return_value=stop_event),
        patch("main.signal.signal") as signal_mock,
    ):
        await main.main()

    application.initialize.assert_awaited_once()
    application.start.assert_awaited_once()
    application.updater.start_polling.assert_awaited_once()
    application.updater.stop.assert_awaited_once()
    application.stop.assert_awaited_once()
    application.shutdown.assert_awaited_once()
    assert signal_mock.call_count == 2

    shutdown_handler = signal_mock.call_args_list[0].args[1]
    shutdown_handler(2, None)
    loop.call_soon_threadsafe.assert_called_once_with(stop_event.set)


@pytest.mark.asyncio
async def test_main_raises_when_updater_missing(test_settings):
    """Отсутствие Updater приводит к явной RuntimeError вместо assert."""
    application = MagicMock()
    application.initialize = AsyncMock()
    application.start = AsyncMock()
    application.updater = None
    loop = MagicMock()
    stop_event = MagicMock()
    stop_event.wait = AsyncMock()

    with (
        patch("main.load_settings", return_value=test_settings),
        patch("main.setup_logging"),
        patch("main.build_application", return_value=application),
        patch("main.asyncio.get_running_loop", return_value=loop),
        patch("main.asyncio.Event", return_value=stop_event),
        patch("main.signal.signal"),
        pytest.raises(RuntimeError, match="Telegram Updater failed to initialize"),
    ):
        await main.main()
