import json
import os
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).parent.parent


class RunnerConfig(BaseModel):
    display_name: str
    strava_athlete_id: int
    spreadsheet_id: str

    @property
    def name(self) -> str:
        return self.display_name.lower()


class RunnerRegistry:
    def __init__(self, runners: dict[str, RunnerConfig]):
        self._by_name = runners
        self._by_athlete_id: dict[int, RunnerConfig] = {
            r.strava_athlete_id: r for r in runners.values()
        }

    @classmethod
    def load(cls, path: Path | None = None) -> "RunnerRegistry":
        raw_config = os.getenv("RUNNERS_CONFIG")
        if raw_config:
            raw = json.loads(raw_config)
        else:
            p = path or Path("runners.json")
            if not p.exists():
                raise FileNotFoundError(
                    "runners.json not found and RUNNERS_CONFIG not set"
                )
            raw = json.loads(p.read_text(encoding="utf-8"))

        runners: dict[str, RunnerConfig] = {}
        seen_names: set[str] = set()

        for key, data in raw.items():
            runner = RunnerConfig(**data)
            name = runner.name
            if name in seen_names:
                raise ValueError(f"Duplicate runner name: '{runner.display_name}'")
            seen_names.add(name)
            runners[name] = runner

        return cls(runners)

    def get_by_name(self, name: str) -> RunnerConfig:
        runner = self._by_name.get(name.lower())
        if runner is None:
            available = list(self._by_name.keys())
            raise KeyError(f"Runner '{name}' not found. Available: {available}")
        return runner

    def get_by_athlete_id(self, athlete_id: int) -> RunnerConfig | None:
        return self._by_athlete_id.get(athlete_id)

    def display_names(self) -> list[str]:
        return [r.display_name for r in self._by_name.values()]


class Settings(BaseSettings):
    strava_client_id: str
    strava_client_secret: str
    strava_refresh_token: str
    strava_verify_token: str

    google_credentials_json: str

    anthropic_api_key: str

    whatsapp_token: str
    whatsapp_phone_number_id: str
    whatsapp_coach_number: str

    model_config = SettingsConfigDict(env_file=str(_PROJECT_ROOT / ".env"))


settings = Settings()
