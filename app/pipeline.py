import anthropic
import logging

from app.config import settings
from app.strava.client import StravaClient
from app.sheets.client import SheetsClient
from app.agents.running_coach import RunningCoachAgent
from app.notifications.whatsapp import WhatsAppClient

log = logging.getLogger(__name__)


async def run_pipeline(activity_id: int) -> None:
    strava = StravaClient(
        settings.strava_client_id,
        settings.strava_client_secret,
        settings.strava_refresh_token,
    )
    sheets = SheetsClient(
        settings.google_credentials_path,
        settings.spreadsheet_id,
    )
    agent = RunningCoachAgent(anthropic.Anthropic(api_key=settings.anthropic_api_key))
    whatsapp = WhatsAppClient(
        settings.whatsapp_token,
        settings.whatsapp_phone_number_id,
    )

    log.info("Fetching activity %s", activity_id)
    activity = strava.get_activity(activity_id)
    log.info("Activity: %s on %s", activity["name"], activity["start_date"])

    tab_name = sheets.find_tab_for_date(settings.runner_name, activity["start_date"])
    log.info("Tab: %s", tab_name)

    planned_session = sheets.get_row_for_date(tab_name, activity["start_date"])
    log.info("Row: %s", planned_session)

    analysis = agent.analyze(activity, planned_session)
    log.info("Analysis:\n%s", analysis)

    sheets.write_analysis(tab_name, planned_session["row_index"], analysis)
    log.info("Written to sheet row %s", planned_session["row_index"])

    result = whatsapp.send_message(settings.runner_whatsapp, analysis)
    print("WhatsApp response:", result)
