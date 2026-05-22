import pytest
from datetime import date
from unittest.mock import MagicMock, patch
from app.sheets.client import SheetsClient

SPREADSHEET_ID = "test_spreadsheet_id"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADER = ["Day", "Date", "Session Type", "Planned", "Distance in km", "Nishant Comments", "AI Comments"]
SAMPLE_ROWS = [
    HEADER,
    ["Sunday", "05/10/2026", "Running", "Easy 5km", "5", "Ran 5k outdoor. Felt heavy at first", ""],
    ["Monday", "05/11/2026", "Strength", "Strength only"],  # trailing empty cols truncated by API
    ["Tuesday", "05/12/2026", "Running", "Easy 10km", "10"],
]


@pytest.fixture
def sheets_client():
    with (
        patch("app.sheets.client.build") as mock_build,
        patch("app.sheets.client.Credentials") as mock_creds,
    ):
        mock_creds.from_service_account_file.return_value = MagicMock()
        client = SheetsClient("credentials.json", SPREADSHEET_ID)
        yield client, mock_build.return_value


def _setup_tabs(mock_service, tab_names: list[str]):
    mock_service.spreadsheets.return_value.get.return_value.execute.return_value = {
        "sheets": [{"properties": {"title": t}} for t in tab_names]
    }


def _setup_rows(mock_service, rows: list):
    mock_service.spreadsheets.return_value.values.return_value.get.return_value.execute.return_value = {
        "values": rows
    }


class TestSheetsClientInit:
    def test_loads_credentials_from_path(self):
        with (
            patch("app.sheets.client.build"),
            patch("app.sheets.client.Credentials") as mock_creds,
        ):
            mock_creds.from_service_account_file.return_value = MagicMock()

            SheetsClient("credentials.json", SPREADSHEET_ID)

            mock_creds.from_service_account_file.assert_called_once_with(
                "credentials.json", scopes=SCOPES
            )

    def test_builds_sheets_service(self):
        with (
            patch("app.sheets.client.build") as mock_build,
            patch("app.sheets.client.Credentials") as mock_creds,
        ):
            creds = MagicMock()
            mock_creds.from_service_account_file.return_value = creds

            SheetsClient("credentials.json", SPREADSHEET_ID)

            mock_build.assert_called_once_with("sheets", "v4", credentials=creds)


class TestFindTabForDate:
    def test_finds_tab_for_same_month_range(self, sheets_client):
        client, mock_service = sheets_client
        _setup_tabs(mock_service, ["May5/15"])

        result = client.find_tab_for_date("Runner", date(2026, 5, 10))

        assert result == "May5/15"

    def test_finds_tab_for_cross_month_range(self, sheets_client):
        client, mock_service = sheets_client
        _setup_tabs(mock_service, ["Apr28/May4"])

        result = client.find_tab_for_date("Runner", date(2026, 5, 3))

        assert result == "Apr28/May4"

    def test_date_on_start_boundary_is_included(self, sheets_client):
        client, mock_service = sheets_client
        _setup_tabs(mock_service, ["May5/15"])

        result = client.find_tab_for_date("Runner", date(2026, 5, 5))

        assert result == "May5/15"

    def test_date_on_end_boundary_is_included(self, sheets_client):
        client, mock_service = sheets_client
        _setup_tabs(mock_service, ["May5/15"])

        result = client.find_tab_for_date("Runner", date(2026, 5, 15))

        assert result == "May5/15"

    def test_skips_non_date_tabs(self, sheets_client):
        client, mock_service = sheets_client
        _setup_tabs(mock_service, ["Sheet1", "Runner Profile", "May5/15"])

        result = client.find_tab_for_date("Runner", date(2026, 5, 10))

        assert result == "May5/15"

    def test_picks_correct_tab_among_multiple(self, sheets_client):
        client, mock_service = sheets_client
        _setup_tabs(mock_service, ["Apr21/27", "Apr28/May4", "May5/15"])

        result = client.find_tab_for_date("Runner", date(2026, 4, 30))

        assert result == "Apr28/May4"

    def test_raises_when_no_tab_matches(self, sheets_client):
        client, mock_service = sheets_client
        _setup_tabs(mock_service, ["Runner_May5/15"])

        with pytest.raises(ValueError, match="No tab found"):
            client.find_tab_for_date("Runner", date(2026, 6, 1))


class TestGetRowForDate:
    def test_returns_dict_with_expected_keys(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        result = client.get_row_for_date("Runner_May5/15", date(2026, 5, 10))

        assert set(result.keys()) == {
            "row_index",
            "day",
            "date",
            "session_type",
            "planned",
            "planned_distance",
            "athlete_comments",
        }

    def test_matches_row_by_date(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        result = client.get_row_for_date("Runner_May5/15", date(2026, 5, 10))

        assert result["date"] == "05/10/2026"
        assert result["session_type"] == "Running"
        assert result["planned"] == "Easy 5km"

    def test_returns_athlete_comments_from_column_f(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        result = client.get_row_for_date("Runner_May5/15", date(2026, 5, 10))

        assert result["athlete_comments"] == "Ran 5k outdoor. Felt heavy at first"

    def test_athlete_comments_empty_string_when_column_f_truncated(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        result = client.get_row_for_date("Runner_May5/15", date(2026, 5, 11))

        assert result["athlete_comments"] == ""

    def test_planned_distance_parsed_as_float(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        result = client.get_row_for_date("Runner_May5/15", date(2026, 5, 10))

        assert result["planned_distance"] == 5.0

    def test_planned_distance_is_none_when_column_truncated(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        result = client.get_row_for_date("Runner_May5/15", date(2026, 5, 11))

        assert result["planned_distance"] is None

    def test_row_index_is_one_indexed_sheet_row(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        result = client.get_row_for_date("Runner_May5/15", date(2026, 5, 10))

        assert result["row_index"] == 2  # header=row1, first data row=row2

    def test_row_index_for_third_data_row(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        result = client.get_row_for_date("Runner_May5/15", date(2026, 5, 12))

        assert result["row_index"] == 4

    def test_fetches_correct_tab(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        client.get_row_for_date("Runner_May5/15", date(2026, 5, 10))

        mock_service.spreadsheets.return_value.values.return_value.get.assert_called_once_with(
            spreadsheetId=SPREADSHEET_ID,
            range="Runner_May5/15!A:G",
        )

    def test_raises_when_date_not_in_tab(self, sheets_client):
        client, mock_service = sheets_client
        _setup_rows(mock_service, SAMPLE_ROWS)

        with pytest.raises(ValueError, match="No row found"):
            client.get_row_for_date("Runner_May5/15", date(2026, 5, 20))


class TestWriteAnalysis:
    def test_writes_to_column_g_with_correct_range(self, sheets_client):
        client, mock_service = sheets_client

        client.write_analysis("Runner_May5/15", 2, "Good effort. Pace on target.")

        mock_service.spreadsheets.return_value.values.return_value.update.assert_called_once_with(
            spreadsheetId=SPREADSHEET_ID,
            range="Runner_May5/15!G2",
            valueInputOption="RAW",
            body={"values": [["Good effort. Pace on target."]]},
        )

    def test_executes_the_update(self, sheets_client):
        client, mock_service = sheets_client

        client.write_analysis("Runner_May5/15", 2, "Analysis text")

        mock_service.spreadsheets.return_value.values.return_value.update.return_value.execute.assert_called_once()

    def test_never_writes_to_column_e_or_f(self, sheets_client):
        client, mock_service = sheets_client

        client.write_analysis("Runner_May5/15", 5, "Some analysis")

        update_call = (
            mock_service.spreadsheets.return_value.values.return_value.update.call_args
        )
        assert "!E" not in update_call.kwargs["range"]
        assert "!F" not in update_call.kwargs["range"]
