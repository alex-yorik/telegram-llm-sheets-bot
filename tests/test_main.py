"""Тесты сборки и запуска приложения."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import handlers
import main
from sheets import SheetsError


def make_builder():
    """Создает мок цепочки Application.builder().token(...).build()."""
    application = MagicMock()
    builder = MagicMock()
    builder.token.return_value.build.return_value = application
    return application, builder


def test_setup_logging():
    """Логирование настраивается один раз и глушит httpx."""
    with (
        patch("main.logging.basicConfig") as basic_config,
        patch("main.logging.getLogger") as get_logger,
    ):
        main.setup_logging()

    basic_config.assert_called_once()
    assert get_logger.call_count == 2


def test_build_application_registers_handlers():
    """Приложение получает три обработчика и клиент Sheets."""
    application, builder = make_builder()
    with (
        patch("main.GoogleSheetsClient") as sheets_class,
        patch("main.Application.builder", return_value=builder),
    ):
        result = main.build_application()

    assert result is application
    assert application.add_handler.call_count == 3
    assert handlers.sheets_client is sheets_class.return_value
    application.bot_data.__setitem__.assert_any_call("sheets_client", sheets_class.return_value)


def test_build_application_without_sheets():
    """При недоступном Sheets бот стартует без записи."""
    application, builder = make_builder()
    with (
        patch("main.GoogleSheetsClient", side_effect=SheetsError("no credentials")),
        patch("main.Application.builder", return_value=builder),
    ):
        result = main.build_application()

    assert result is application
    assert handlers.sheets_client is None
    application.bot_data.__setitem__.assert_any_call("sheets_client", None)


@pytest.mark.asyncio
async def test_main_starts_and_stops():
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
