"""Google Sheets integration for saving leads."""

import datetime
import logging

import gspread
from google.oauth2.service_account import Credentials

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
    """Google Sheets operation error."""


class GoogleSheetsClient:
    """Client for writing leads to a Google Spreadsheet."""

    def __init__(
        self,
        credentials_path: str,
        spreadsheet_id: str,
        sheet_name: str = "Sheet1",
    ) -> None:
        self._credentials_path = credentials_path
        self._spreadsheet_id = spreadsheet_id
        self._sheet_name = sheet_name
        try:
            creds = Credentials.from_service_account_file(self._credentials_path, scopes=_SCOPES)
            self._client = gspread.authorize(creds)
            logger.info("GoogleSheetsClient initialized (sheet=%s)", self._sheet_name)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to initialize GoogleSheetsClient (%s)", type(exc).__name__)
            raise SheetsError(str(exc)) from exc

    def _get_worksheet(self) -> gspread.Worksheet:
        """Opens a worksheet by name or returns the first sheet."""
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
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to open spreadsheet (%s)", type(exc).__name__)
            raise SheetsError(str(exc)) from exc

    def append_lead(
        self,
        lead: Lead,
        original_message: str,
        correlation_id: str | None = None,
    ) -> None:
        """Appends a row with lead data to the spreadsheet."""
        try:
            worksheet = self._get_worksheet()
            first_row = worksheet.row_values(1)
            is_empty = not first_row or all(not cell.strip() for cell in first_row)
            if is_empty:
                if first_row:
                    worksheet.clear()
                worksheet.append_row(HEADER, value_input_option="RAW")
                logger.info("Header row added: %s", HEADER)
            created_at = datetime.datetime.now(datetime.UTC).isoformat()
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
            logger.info("Lead saved to spreadsheet (correlation_id=%s)", correlation_id)
        except SheetsError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to save lead to spreadsheet (%s)", type(exc).__name__)
            raise SheetsError(str(exc)) from exc
