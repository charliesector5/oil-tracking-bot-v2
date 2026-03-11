import logging
from typing import List, Optional

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from config import settings

log = logging.getLogger(__name__)

_WORKSHEET = None


def init_gsheet():
    global _WORKSHEET

    log.info("🔐 Connecting to Google Sheets...")
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        settings.google_credentials_path,
        scope,
    )
    client = gspread.authorize(creds)
    _WORKSHEET = client.open_by_key(settings.google_sheet_id).sheet1
    log.info("✅ Google Sheets ready.")


def get_worksheet():
    if _WORKSHEET is None:
        raise RuntimeError("Google Sheet is not initialised yet.")
    return _WORKSHEET


def get_all_rows() -> List[List[str]]:
    ws = get_worksheet()
    return ws.get_all_values()


def get_row_count() -> int:
    rows = get_all_rows()
    return len(rows)


def get_header_row() -> List[str]:
    rows = get_all_rows()
    if not rows:
        return []
    return rows[0]


def append_row(row: List[str]) -> None:
    ws = get_worksheet()
    ws.append_row(row, value_input_option="USER_ENTERED")


def healthcheck() -> tuple[bool, str]:
    try:
        ws = get_worksheet()
        title = ws.title
        count = get_row_count()
        return True, f"Sheet OK: {title} | rows={count}"
    except Exception as exc:
        log.exception("Google Sheet healthcheck failed")
        return False, f"Sheet error: {exc}"


def try_get_worksheet_title() -> Optional[str]:
    try:
        ws = get_worksheet()
        return ws.title
    except Exception:
        return None
