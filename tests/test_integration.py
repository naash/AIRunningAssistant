"""
Integration tests — hit the real Google Sheets API.

Requirements:
  - credentials.json present (path from GOOGLE_CREDENTIALS_PATH env var)
  - SPREADSHEET_ID set in .env or environment
  - RUNNER_NAME set so the current week's tab can be located

Run with:
  pytest -m integration
"""

import os
import pytest
from datetime import date

pytestmark = pytest.mark.integration

TEST_ROW = 15
TEST_VALUE = "integration_test_marker, content pushed from Nishant's app directly (WIP) — safe to delete"


@pytest.fixture(scope="module")
def real_sheets_client():
    from app.config import settings
    from app.sheets.client import SheetsClient

    creds_path = settings.google_credentials_path
    spreadsheet_id = settings.spreadsheet_id
    runner_name = settings.runner_name

    if not os.path.exists(creds_path):
        pytest.skip(f"credentials file not found: {creds_path}")

    return SheetsClient(creds_path, spreadsheet_id)


@pytest.fixture(scope="module")
def active_tab(real_sheets_client):
    from app.config import settings

    try:
        return real_sheets_client.find_tab_for_date(settings.runner_name, date.today())
    except ValueError:
        pytest.skip(
            f"No active tab found for {settings.runner_name} on {date.today()} — create one in the sheet first"
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

    # def test_cleanup(self, real_sheets_client, active_tab):
    #     real_sheets_client._service.spreadsheets().values().clear(
    #         spreadsheetId=real_sheets_client._spreadsheet_id,
    #         range=f"{active_tab}!F{TEST_ROW}",
    #     ).execute()

    #     result = (
    #         real_sheets_client._service.spreadsheets()
    #         .values()
    #         .get(
    #             spreadsheetId=real_sheets_client._spreadsheet_id,
    #             range=f"{active_tab}!F{TEST_ROW}",
    #         )
    #         .execute()
    #     )

    #     assert result.get("values") is None
