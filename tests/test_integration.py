"""
Integration tests — hit the real Google Sheets API.

Requirements:
  - credentials.json present (path from GOOGLE_CREDENTIALS_PATH env var)
  - runners.json present with at least one runner configured
  - The runner's active tab must exist in their spreadsheet

Run with:
  pytest -m integration
"""

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

    if not settings.google_credentials_json:
        pytest.skip("GOOGLE_CREDENTIALS_JSON not set")

    return SheetsClient(settings.google_credentials_json, runner.spreadsheet_id)


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
        print(f"Writing to: {active_tab}!G{TEST_ROW}")

        real_sheets_client.write_analysis(active_tab, TEST_ROW, TEST_VALUE)

        result = (
            real_sheets_client._service.spreadsheets()
            .values()
            .get(
                spreadsheetId=real_sheets_client._spreadsheet_id,
                range=f"{active_tab}!G{TEST_ROW}",
            )
            .execute()
        )

        written = result.get("values", [[""]])[0][0]
        print(f"Value read back: {written!r}")
        assert written == TEST_VALUE

    def test_write_does_not_touch_column_e_or_f(self, real_sheets_client, active_tab):
        print(f"\nChecking columns E and F are untouched at row {TEST_ROW}")

        for col in ("E", "F"):
            result = (
                real_sheets_client._service.spreadsheets()
                .values()
                .get(
                    spreadsheetId=real_sheets_client._spreadsheet_id,
                    range=f"{active_tab}!{col}{TEST_ROW}",
                )
                .execute()
            )
            value = result.get("values", [[""]])[0][0] if result.get("values") else ""
            print(f"Column {col} value: {value!r}")
            assert value == "", f"Column {col} should be empty but got {value!r}"

    def test_written_value_persists(self, real_sheets_client, active_tab):
        print(f"\nVerifying value persists at {active_tab}!G{TEST_ROW}")

        result = (
            real_sheets_client._service.spreadsheets()
            .values()
            .get(
                spreadsheetId=real_sheets_client._spreadsheet_id,
                range=f"{active_tab}!G{TEST_ROW}",
            )
            .execute()
        )

        written = result.get("values", [[""]])[0][0]
        print(f"Value found: {written!r}")
        assert written == TEST_VALUE
