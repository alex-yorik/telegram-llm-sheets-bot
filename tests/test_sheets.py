"""Тесты клиента Google Sheets (сеть замокана)."""

from unittest.mock import MagicMock, patch

import gspread
import pytest

from models import Lead
from sheets import HEADER, GoogleSheetsClient, SheetsError


def build_client() -> GoogleSheetsClient:
    """Создает клиент с замоканными credentials и gspread."""
    with (
        patch("sheets.Credentials.from_service_account_file") as credentials,
        patch("sheets.gspread.authorize") as authorize,
    ):
        credentials.return_value = MagicMock()
        authorize.return_value = MagicMock()
        return GoogleSheetsClient(
            credentials_path="/tmp/fake-credentials.json",
            spreadsheet_id="test-spreadsheet-id",
            sheet_name="Sheet1",
        )


def test_client_initialization():
    """Клиент сохраняет переданные параметры."""
    client = build_client()

    assert client._spreadsheet_id == "test-spreadsheet-id"
    assert client._sheet_name == "Sheet1"


def test_client_requires_explicit_configuration():
    """Клиент не подхватывает конфигурацию неявно из глобального объекта."""
    with pytest.raises(TypeError):
        GoogleSheetsClient()


def test_client_initialization_error():
    """Ошибка загрузки credentials превращается в SheetsError."""
    with (
        patch(
            "sheets.Credentials.from_service_account_file",
            side_effect=OSError("cannot read"),
        ),
        pytest.raises(SheetsError),
    ):
        GoogleSheetsClient(
            credentials_path="/tmp/missing.json",
            spreadsheet_id="test",
            sheet_name="Sheet1",
        )


def test_get_worksheet_by_name():
    """Worksheet находится по имени."""
    client = build_client()
    worksheet = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheet.return_value = worksheet
    client._client.open_by_key.return_value = spreadsheet

    assert client._get_worksheet() is worksheet
    spreadsheet.worksheet.assert_called_once_with("Sheet1")


def test_get_worksheet_fallback_to_first_sheet():
    """При отсутствии листа используется первый."""
    client = build_client()
    worksheet = MagicMock()
    spreadsheet = MagicMock()
    spreadsheet.worksheet.side_effect = gspread.WorksheetNotFound("Sheet1")
    spreadsheet.sheet1 = worksheet
    client._client.open_by_key.return_value = spreadsheet

    assert client._get_worksheet() is worksheet


def test_get_worksheet_open_error():
    """Ошибка открытия таблицы превращается в SheetsError."""
    client = build_client()
    client._client.open_by_key.side_effect = RuntimeError("boom")

    with pytest.raises(SheetsError):
        client._get_worksheet()


def test_get_worksheet_reraises_sheets_error():
    """SheetsError не заворачивается повторно."""
    client = build_client()
    client._client.open_by_key.side_effect = SheetsError("already wrapped")

    with pytest.raises(SheetsError, match="already wrapped"):
        client._get_worksheet()


def test_append_lead_success():
    """Строка заявки добавляется с RAW-вводом."""
    client = build_client()
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = [HEADER]
    client._get_worksheet = MagicMock(return_value=worksheet)
    lead = Lead(
        name="John",
        phone="+123",
        service="English",
        date="Tuesday",
        time="17:00",
    )

    client.append_lead(lead, "original message", correlation_id="test-correlation-id")

    worksheet.append_row.assert_called_once()
    row = worksheet.append_row.call_args.args[0]
    assert row[:5] == ["John", "+123", "English", "Tuesday", "17:00"]
    assert row[5] == "original message"
    assert row[6]
    assert worksheet.append_row.call_args.kwargs["value_input_option"] == "RAW"
    worksheet.clear.assert_not_called()


def test_append_lead_creates_header_if_empty():
    """В пустую таблицу сначала пишется заголовок."""
    client = build_client()
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = []
    client._get_worksheet = MagicMock(return_value=worksheet)

    client.append_lead(Lead(name="John"), "", correlation_id=None)

    assert worksheet.append_row.call_count == 2
    assert worksheet.append_row.call_args_list[0].args[0] == HEADER
    worksheet.clear.assert_not_called()


def test_append_lead_clears_whitespace_only_sheet():
    """Таблица из пустых ячеек очищается перед заголовком."""
    client = build_client()
    worksheet = MagicMock()
    worksheet.get_all_values.return_value = [["   ", ""]]
    client._get_worksheet = MagicMock(return_value=worksheet)

    client.append_lead(Lead(name="John"), "", correlation_id=None)

    worksheet.clear.assert_called_once()
    assert worksheet.append_row.call_count == 2


def test_append_lead_sheets_error():
    """Ошибка записи превращается в SheetsError."""
    client = build_client()
    worksheet = MagicMock()
    worksheet.get_all_values.side_effect = RuntimeError("Sheets Error")
    client._get_worksheet = MagicMock(return_value=worksheet)

    with pytest.raises(SheetsError):
        client.append_lead(Lead(name="John"), "", correlation_id=None)


def test_append_lead_reraises_sheets_error():
    """SheetsError из _get_worksheet не заворачивается повторно."""
    client = build_client()
    client._get_worksheet = MagicMock(side_effect=SheetsError("already wrapped"))

    with pytest.raises(SheetsError, match="already wrapped"):
        client.append_lead(Lead(name="John"), "", correlation_id=None)
