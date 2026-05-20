import anthropic
import logging

from app.config import RunnerConfig, settings
from app.strava.client import StravaClient
from app.sheets.client import SheetsClient
from app.agents.running_coach import RunningCoachAgent
from app.notifications.whatsapp import WhatsAppClient
from app.weather import get_weather

log = logging.getLogger(__name__)


async def run_pipeline(activity_id: int, runner: RunnerConfig) -> dict:
    strava = StravaClient(
        settings.strava_client_id,
        settings.strava_client_secret,
        settings.strava_refresh_token,
    )
    sheets = SheetsClient(
        settings.google_credentials_path,
        runner.spreadsheet_id,
    )
    agent = RunningCoachAgent(
        anthropic.Anthropic(api_key=settings.anthropic_api_key),
        runner_md_path=runner.profile_path,
    )
    whatsapp = WhatsAppClient(
        settings.whatsapp_token,
        settings.whatsapp_phone_number_id,
    )

    log.info("Fetching activity %s", activity_id)
    activity = strava.get_activity(activity_id)
    log.info("Activity: %s on %s", activity["name"], activity["start_date"])

    tab_name = sheets.find_tab_for_date(runner.display_name, activity["start_date"])
    log.info("Tab: %s", tab_name)

    planned_session = sheets.get_row_for_date(tab_name, activity["start_date"])
    log.info("Row: %s", planned_session)

    weather = await get_weather(activity["start_latlng"], activity["start_date_local"])

    analysis = agent.analyze(activity, planned_session, weather)
    log.info("Analysis:\n%s", analysis)

    sheets.write_analysis(tab_name, planned_session["row_index"], analysis)
    log.info("Written to sheet row %s", planned_session["row_index"])

    result = whatsapp.send_message(settings.whatsapp_coach_number, analysis)
    print("WhatsApp response:", result)

    return activity
