"""
Integration tests — hit the real Google Sheets API.

Requirements:
  - credentials.json present (path from GOOGLE_CREDENTIALS_PATH env var)
  - runners.json present with at least one runner configured
  - The runner's active tab must exist in their spreadsheet

Run with:
  pytest -m integration
"""

import os
import pytest
from datetime import date
from pathlib import Path

pytestmark = pytest.mark.integration

TEST_ROW = 15
TEST_VALUE = "integration_test_marker, content pushed from Nishant's app directly (WIP) — safe to delete"

_RUNNERS_JSON = Path(__file__).parent.parent / "runners.json"


@pytest.fixture(scope="module")
def runner():
    from app.config import RunnerRegistry

    if not _RUNNERS_JSON.exists():
        pytest.skip("runners.json not found")

    registry = RunnerRegistry.load(_RUNNERS_JSON)
    names = list(registry._by_name.keys())
    if not names:
        pytest.skip("No runners configured in runners.json")
    return registry.get_by_name(names[0])


@pytest.fixture(scope="module")
def real_sheets_client(runner):
    from app.config import settings
    from app.sheets.client import SheetsClient

    creds_path = settings.google_credentials_path
    if not os.path.exists(creds_path):
        pytest.skip(f"credentials file not found: {creds_path}")

    return SheetsClient(creds_path, runner.spreadsheet_id)


@pytest.fixture(scope="module")
def active_tab(real_sheets_client, runner):
    try:
        return real_sheets_client.find_tab_for_date(runner.display_name, date.today())
    except ValueError:
        pytest.skip(
            f"No active tab found for {runner.display_name} on {date.today()} — create one in the sheet first"
        )


class TestSheetsWriteIntegration:
    def test_write_analysis_updates_correct_cell(self, real_sheets_client, active_tab):
        print(f"\nSpreadsheet ID: {real_sheets_client._spreadsheet_id}")
        print(f"Tab: {active_tab}")
        print(f"Writing to: {active_tab}!F{TEST_ROW}")

        real_sheets_client.write_analysis(active_tab, TEST_ROW, TEST_VALUE)

        result = (
            real_sheets_client._service.spreadsheets()
            .values()
            .get(
                spreadsheetId=real_sheets_client._spreadsheet_id,
                range=f"{active_tab}!F{TEST_ROW}",
            )
            .execute()
        )

        written = result.get("values", [[""]])[0][0]
        print(f"Value read back: {written!r}")
        assert written == TEST_VALUE

    def test_write_does_not_touch_column_e(self, real_sheets_client, active_tab):
        print(f"\nChecking column E is untouched at row {TEST_ROW}")

        result = (
            real_sheets_client._service.spreadsheets()
            .values()
            .get(
                spreadsheetId=real_sheets_client._spreadsheet_id,
                range=f"{active_tab}!E{TEST_ROW}",
            )
            .execute()
        )

        col_e = result.get("values", [[""]])[0][0] if result.get("values") else ""
        print(f"Column E value: {col_e!r}")
        assert col_e == ""

    def test_written_value_persists(self, real_sheets_client, active_tab):
        print(f"\nVerifying value persists at {active_tab}!F{TEST_ROW}")

        result = (
            real_sheets_client._service.spreadsheets()
            .values()
            .get(
                spreadsheetId=real_sheets_client._spreadsheet_id,
                range=f"{active_tab}!F{TEST_ROW}",
            )
            .execute()
        )

        written = result.get("values", [[""]])[0][0]
        print(f"Value found: {written!r}")
        assert written == TEST_VALUE
