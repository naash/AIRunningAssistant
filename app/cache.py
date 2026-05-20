import json
from datetime import datetime
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"


def _cache_file(runner_name: str) -> Path:
    return _DATA_DIR / runner_name / "last_processed.json"


def save_last_processed(runner_name: str, activity_id: int, start_date_local: datetime) -> None:
    path = _cache_file(runner_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({
            "activity_id": activity_id,
            "start_date_local": start_date_local.isoformat(),
        })
    )


def load_last_processed(runner_name: str) -> dict | None:
    path = _cache_file(runner_name)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    data["start_date_local"] = datetime.fromisoformat(data["start_date_local"])
    return data
