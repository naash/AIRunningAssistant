import pytest
from datetime import date
from unittest.mock import MagicMock, patch, call
from app.pipeline import run_pipeline
from app.config import settings

ACTIVITY_ID = 12345678
TAB_NAME = "Runner_May5/15"
ANALYSIS = "Good effort. Ran further than planned. Pace consistent."

SAMPLE_ACTIVITY = {
    "id": ACTIVITY_ID,
    "name": "Morning Run",
    "type": "Run",
    "sport_type": "Run",
    "start_date": date(2026, 5, 10),
    "distance": 5020.0,
    "moving_time": 1860,
}

SAMPLE_ROW = {
    "row_index": 2,
    "day": "Sunday",
    "date": "05/10/2026",
    "session_type": "Walk",
    "planned": "4km walk",
    "athlete_comments": "",
}


@pytest.fixture
def mock_clients():
    with patch("app.pipeline.StravaClient") as mock_strava_cls, \
         patch("app.pipeline.SheetsClient") as mock_sheets_cls, \
         patch("app.pipeline.RunningCoachAgent") as mock_agent_cls, \
         patch("app.pipeline.WhatsAppClient") as mock_whatsapp_cls, \
         patch("app.pipeline.anthropic.Anthropic"):

        mock_strava = MagicMock()
        mock_strava_cls.return_value = mock_strava
        mock_strava.get_activity.return_value = SAMPLE_ACTIVITY

        mock_sheets = MagicMock()
        mock_sheets_cls.return_value = mock_sheets
        mock_sheets.find_tab_for_date.return_value = TAB_NAME
        mock_sheets.get_row_for_date.return_value = SAMPLE_ROW

        mock_agent = MagicMock()
        mock_agent_cls.return_value = mock_agent
        mock_agent.analyze.return_value = ANALYSIS

        mock_whatsapp = MagicMock()
        mock_whatsapp_cls.return_value = mock_whatsapp

        yield {
            "strava": mock_strava,
            "sheets": mock_sheets,
            "agent": mock_agent,
            "whatsapp": mock_whatsapp,
        }


class TestPipelineClients:
    async def test_strava_client_initialised_from_settings(self, mock_clients):
        with patch("app.pipeline.StravaClient") as mock_cls, \
             patch("app.pipeline.SheetsClient"), \
             patch("app.pipeline.RunningCoachAgent"), \
             patch("app.pipeline.WhatsAppClient"), \
             patch("app.pipeline.anthropic.Anthropic"):
            mock_cls.return_value = mock_clients["strava"]
            await run_pipeline(ACTIVITY_ID)

            mock_cls.assert_called_once_with(
                settings.strava_client_id,
                settings.strava_client_secret,
                settings.strava_refresh_token,
            )

    async def test_sheets_client_initialised_from_settings(self, mock_clients):
        with patch("app.pipeline.StravaClient") as _strava, \
             patch("app.pipeline.SheetsClient") as mock_cls, \
             patch("app.pipeline.RunningCoachAgent"), \
             patch("app.pipeline.WhatsAppClient"), \
             patch("app.pipeline.anthropic.Anthropic"):
            _strava.return_value = mock_clients["strava"]
            mock_cls.return_value = mock_clients["sheets"]
            await run_pipeline(ACTIVITY_ID)

            mock_cls.assert_called_once_with(
                settings.google_credentials_path,
                settings.spreadsheet_id,
            )

    async def test_whatsapp_client_initialised_from_settings(self, mock_clients):
        with patch("app.pipeline.StravaClient") as _strava, \
             patch("app.pipeline.SheetsClient") as _sheets, \
             patch("app.pipeline.RunningCoachAgent"), \
             patch("app.pipeline.WhatsAppClient") as mock_cls, \
             patch("app.pipeline.anthropic.Anthropic"):
            _strava.return_value = mock_clients["strava"]
            _sheets.return_value = mock_clients["sheets"]
            mock_cls.return_value = mock_clients["whatsapp"]
            await run_pipeline(ACTIVITY_ID)

            mock_cls.assert_called_once_with(
                settings.whatsapp_token,
                settings.whatsapp_phone_number_id,
            )


class TestPipelineSteps:
    async def test_fetches_activity_by_id(self, mock_clients):
        await run_pipeline(ACTIVITY_ID)

        mock_clients["strava"].get_activity.assert_called_once_with(ACTIVITY_ID)

    async def test_finds_tab_using_activity_date_and_runner_name(self, mock_clients):
        await run_pipeline(ACTIVITY_ID)

        mock_clients["sheets"].find_tab_for_date.assert_called_once_with(
            settings.runner_name, date(2026, 5, 10)
        )

    async def test_gets_row_using_tab_and_activity_date(self, mock_clients):
        await run_pipeline(ACTIVITY_ID)

        mock_clients["sheets"].get_row_for_date.assert_called_once_with(
            TAB_NAME, date(2026, 5, 10)
        )

    async def test_agent_receives_activity_and_planned_session(self, mock_clients):
        await run_pipeline(ACTIVITY_ID)

        mock_clients["agent"].analyze.assert_called_once_with(SAMPLE_ACTIVITY, SAMPLE_ROW)

    async def test_writes_analysis_to_correct_tab_and_row(self, mock_clients):
        await run_pipeline(ACTIVITY_ID)

        mock_clients["sheets"].write_analysis.assert_called_once_with(
            TAB_NAME, SAMPLE_ROW["row_index"], ANALYSIS
        )

    async def test_sends_whatsapp_to_runner_number(self, mock_clients):
        await run_pipeline(ACTIVITY_ID)

        mock_clients["whatsapp"].send_message.assert_called_once_with(
            settings.runner_whatsapp, ANALYSIS
        )

    async def test_analysis_written_before_whatsapp_sent(self, mock_clients):
        call_order = []
        mock_clients["sheets"].write_analysis.side_effect = lambda *a, **kw: call_order.append("write")
        mock_clients["whatsapp"].send_message.side_effect = lambda *a, **kw: call_order.append("whatsapp")

        await run_pipeline(ACTIVITY_ID)

        assert call_order == ["write", "whatsapp"]


class TestPipelineErrorHandling:
    async def test_no_tab_found_stops_pipeline(self, mock_clients):
        mock_clients["sheets"].find_tab_for_date.side_effect = ValueError("No tab found")

        with pytest.raises(ValueError):
            await run_pipeline(ACTIVITY_ID)

        mock_clients["agent"].analyze.assert_not_called()
        mock_clients["sheets"].write_analysis.assert_not_called()
        mock_clients["whatsapp"].send_message.assert_not_called()

    async def test_no_row_found_stops_pipeline(self, mock_clients):
        mock_clients["sheets"].get_row_for_date.side_effect = ValueError("No row found")

        with pytest.raises(ValueError):
            await run_pipeline(ACTIVITY_ID)

        mock_clients["agent"].analyze.assert_not_called()
        mock_clients["sheets"].write_analysis.assert_not_called()
        mock_clients["whatsapp"].send_message.assert_not_called()
