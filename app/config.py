from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    strava_client_id: str
    strava_client_secret: str
    strava_refresh_token: str
    strava_verify_token: str
    strava_athlete_id: int

    runner_name: str
    runner_whatsapp: str

    google_credentials_path: str
    spreadsheet_id: str

    anthropic_api_key: str

    whatsapp_token: str
    whatsapp_phone_number_id: str

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env")
    )


settings = Settings()

