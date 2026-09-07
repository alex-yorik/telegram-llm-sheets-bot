"""Интеграция с Google Sheets для сохранения заявок."""

import datetime
import logging

import gspread
from google.oauth2.service_account import Credentials

from config import settings
from models import Lead

logger = logging.getLogger(__name__)

HEADER = [
    "Name",
    "Phone",
    "Service",
    "Date",
    "Time",
    "Original Message",
    "Created At",
]

_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetsError(Exception):
    """Ошибка работы с Google Sheets."""


class GoogleSheetsClient:
    """Клиент для записи заявок в Google Таблицу."""

    def __init__(
        self,
        credentials_path: str | None = None,
        spreadsheet_id: str | None = None,
        sheet_name: str | None = None,
    ) -> None:
        self._credentials_path = (
            credentials_path or settings.google_application_credentials
        )
        self._spreadsheet_id = (
            spreadsheet_id or settings.google_spreadsheet_id
        )
        self._sheet_name = sheet_name or settings.google_sheet_name
        try:
            creds = Credentials.from_service_account_file(
                self._credentials_path, scopes=_SCOPES
            )
            self._client = gspread.authorize(creds)
            logger.info(
                "GoogleSheetsClient initialized: spreadsheet_id=%s "
                "sheet=%s creds=%s",
                self._spreadsheet_id,
                self._sheet_name,
                self._credentials_path,
            )
        except Exception as exc:
            logger.exception("Failed to initialize GoogleSheetsClient")
            raise SheetsError(str(exc)) from exc

    def _get_worksheet(self) -> gspread.Worksheet:
        """Открывает worksheet по имени или возвращает первый лист."""
        try:
            spreadsheet = self._client.open_by_key(self._spreadsheet_id)
            try:
                return spreadsheet.worksheet(self._sheet_name)
            except gspread.WorksheetNotFound:
                logger.warning(
                    "Sheet %r not found, using the first sheet",
                    self._sheet_name,
                )
                return spreadsheet.sheet1
        except SheetsError:
            raise
        except Exception as exc:
            logger.exception("Failed to open spreadsheet")
            raise SheetsError(str(exc)) from exc

    def append_lead(self, lead: Lead, original_message: str) -> None:
        """Добавляет строку с данными заявки в таблицу."""
        try:
            worksheet = self._get_worksheet()
            values = worksheet.get_all_values()
            is_empty = not values or all(
                not any(cell.strip() for cell in row) for row in values
            )
            if is_empty:
                if values:
                    worksheet.clear()
                worksheet.append_row(HEADER, value_input_option="RAW")
                logger.info("Header row added: %s", HEADER)
            created_at = datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
            row = [
                lead.name or "",
                lead.phone or "",
                lead.service or "",
                lead.date or "",
                lead.time or "",
                original_message or "",
                created_at,
            ]
            worksheet.append_row(row, value_input_option="RAW")
            logger.info("Lead saved to spreadsheet: %s", row)
        except SheetsError:
            raise
        except Exception as exc:
            logger.exception("Failed to save lead to spreadsheet")
            raise SheetsError(str(exc)) from exc
