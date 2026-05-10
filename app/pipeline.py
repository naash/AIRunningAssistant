import anthropic

from app.config import settings
from app.strava.client import StravaClient
from app.sheets.client import SheetsClient
from app.agents.running_coach import RunningCoachAgent
from app.notifications.whatsapp import WhatsAppClient


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

    activity = strava.get_activity(activity_id)
    tab_name = sheets.find_tab_for_date(settings.runner_name, activity["start_date"])
    planned_session = sheets.get_row_for_date(tab_name, activity["start_date"])
    analysis = agent.analyze(activity, planned_session)
    sheets.write_analysis(tab_name, planned_session["row_index"], analysis)
    whatsapp.send_message(settings.runner_whatsapp, analysis)
