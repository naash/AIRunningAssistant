import os
import pytest
from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault("STRAVA_CLIENT_ID", "test_client_id")
os.environ.setdefault("STRAVA_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("STRAVA_REFRESH_TOKEN", "test_refresh_token")
os.environ.setdefault("STRAVA_VERIFY_TOKEN", "test_verify_token")
os.environ.setdefault("STRAVA_ATHLETE_ID", "41195238")
os.environ.setdefault("RUNNER_NAME", "TestRunner")
os.environ.setdefault("RUNNER_WHATSAPP", "+10000000000")
os.environ.setdefault("GOOGLE_CREDENTIALS_PATH", "google-sheets-credentials.json")
os.environ.setdefault("SPREADSHEET_ID", "test_spreadsheet_id")
os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")
os.environ.setdefault("WHATSAPP_TOKEN", "test_whatsapp_token")
os.environ.setdefault("WHATSAPP_PHONE_NUMBER_ID", "test_phone_number_id")


@pytest.fixture
def sample_activity():
    return {
        "id": 12345678,
        "name": "Morning Run",
        "distance": 5020.0,
        "moving_time": 1860,
        "elapsed_time": 1920,
        "start_date": "2026-05-10T07:00:00Z",
        "average_speed": 2.70,
        "average_heartrate": None,
        "type": "Run",
    }


@pytest.fixture
def sample_row():
    return {
        "row_index": 7,
        "day": "Sunday",
        "date": "05/10/2026",
        "session_type": "Walk",
        "planned": "4km walk",
        "athlete_comments": "Ran 5k outdoor. Legs felt heavy at the start but by the end, they felt fine",
    }
