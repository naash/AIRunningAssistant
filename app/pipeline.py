import anthropic
import logging
from datetime import date as DateType

from app.config import RunnerConfig, settings
from app.strava.client import StravaClient
from app.sheets.client import SheetsClient
from app.agents.running_coach import RunningCoachAgent
from app.notifications.whatsapp import WhatsAppClient
from app.weather import get_weather

log = logging.getLogger(__name__)


async def run_pipeline(
    runner: RunnerConfig,
    activity_id: int | None = None,
    on_date: DateType | None = None,
) -> dict:
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

    if activity_id is not None:
        log.info("Fetching activity %s", activity_id)
        activity = strava.get_activity(activity_id)
        tab_name = sheets.find_tab_for_date(runner.display_name, activity["start_date"])
        planned_session = sheets.get_row_for_date(tab_name, activity["start_date"])
    elif on_date is not None:
        log.info("Matching activity for %s on %s", runner.display_name, on_date)
        tab_name = sheets.find_tab_for_date(runner.display_name, on_date)
        planned_session = sheets.get_row_for_date(tab_name, on_date)
        activities = strava.get_activities_on_date(on_date, planned_session["session_type"])
        matched = strava.find_best_match(activities, planned_session["planned_distance"])
        activity = strava.get_activity(matched["id"])
    else:
        raise ValueError("Either activity_id or on_date must be provided")

    log.info("Activity: %s on %s", activity["name"], activity["start_date"])
    log.info("Tab: %s, Row: %s", tab_name, planned_session["row_index"])

    weather = await get_weather(activity["start_latlng"], activity["start_date_local"])

    analysis = agent.analyze(activity, planned_session, weather)
    log.info("Analysis:\n%s", analysis)

    sheets.write_analysis(tab_name, planned_session["row_index"], analysis)
    log.info("Written to sheet row %s", planned_session["row_index"])

    result = whatsapp.send_message(settings.whatsapp_coach_number, analysis)
    print("WhatsApp response:", result)

    return activity
