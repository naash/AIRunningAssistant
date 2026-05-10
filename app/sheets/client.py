import re
from datetime import date, datetime
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class SheetsClient:
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        self._spreadsheet_id = spreadsheet_id
        creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
        self._service = build("sheets", "v4", credentials=creds)

    def find_tab_for_date(self, runner_name: str, activity_date: date) -> str:
        meta = self._service.spreadsheets().get(
            spreadsheetId=self._spreadsheet_id
        ).execute()
        tabs = [s["properties"]["title"] for s in meta["sheets"]]

        prefix = f"{runner_name}_"
        for tab in tabs:
            if not tab.startswith(prefix):
                continue
            try:
                start, end = _parse_tab_date_range(tab[len(prefix):], activity_date.year)
                if start <= activity_date <= end:
                    return tab
            except ValueError:
                continue

        raise ValueError(f"No tab found for {runner_name} on {activity_date}")

    def get_row_for_date(self, tab_name: str, activity_date: date) -> dict:
        result = self._service.spreadsheets().values().get(
            spreadsheetId=self._spreadsheet_id,
            range=f"{tab_name}!A:F",
        ).execute()
        values = result.get("values", [])

        target = activity_date.strftime("%m/%d/%Y")
        for i, row in enumerate(values):
            if i == 0:
                continue
            if len(row) > 1 and row[1] == target:
                return {
                    "row_index": i + 1,
                    "day": row[0] if len(row) > 0 else "",
                    "date": row[1],
                    "session_type": row[2] if len(row) > 2 else "",
                    "planned": row[3] if len(row) > 3 else "",
                    "athlete_comments": row[4] if len(row) > 4 else "",
                }

        raise ValueError(f"No row found for {activity_date} in {tab_name}")

    def write_analysis(self, tab_name: str, row_index: int, analysis: str) -> None:
        self._service.spreadsheets().values().update(
            spreadsheetId=self._spreadsheet_id,
            range=f"{tab_name}!F{row_index}",
            valueInputOption="RAW",
            body={"values": [[analysis]]},
        ).execute()


def _parse_tab_date_range(date_range: str, year: int) -> tuple[date, date]:
    """Parse tab date range string into (start, end) dates.

    Formats:
      May5/15      → same month, May 5 – May 15
      Apr28/May4   → cross-month, Apr 28 – May 4
    """
    left, right = date_range.split("/")

    left_match = re.fullmatch(r"([A-Za-z]+)(\d+)", left)
    if not left_match:
        raise ValueError(f"Cannot parse left part: {left}")
    start_month_str, start_day = left_match.group(1), int(left_match.group(2))

    right_match = re.fullmatch(r"([A-Za-z]*)(\d+)", right)
    if not right_match:
        raise ValueError(f"Cannot parse right part: {right}")
    end_month_str = right_match.group(1) or start_month_str
    end_day = int(right_match.group(2))

    start_month = datetime.strptime(start_month_str, "%b").month
    end_month = datetime.strptime(end_month_str, "%b").month

    start_year = year
    end_year = year
    if start_month > end_month:
        start_year = year - 1

    return (
        date(start_year, start_month, start_day),
        date(end_year, end_month, end_day),
    )
