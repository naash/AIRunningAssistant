import json
from datetime import datetime
from pathlib import Path

_CACHE_FILE = Path(__file__).parent.parent / "data" / "last_processed.json"


def save_last_processed(activity_id: int, start_date_local: datetime) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_FILE.write_text(
        json.dumps({
            "activity_id": activity_id,
            "start_date_local": start_date_local.isoformat(),
        })
    )


def load_last_processed() -> dict | None:
    if not _CACHE_FILE.exists():
        return None
    data = json.loads(_CACHE_FILE.read_text())
    data["start_date_local"] = datetime.fromisoformat(data["start_date_local"])
    return data
