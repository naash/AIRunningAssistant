"""
Endpoints
---------
POST /webhook/strava          Strava push notification handler (production use).
GET  /webhook/strava          Strava webhook subscription verification.

POST /process-recent          Process one activity and cache it.
                              Body (optional): {"activity_id": 12345}
                              Omit body to process the athlete's most recent activity.
                              Example:
                                curl -X POST http://localhost:8000/process-recent
                                curl -X POST http://localhost:8000/process-recent \
                                     -H "Content-Type: application/json" \
                                     -d '{"activity_id": 12345678}'

POST /update-since-last       Process all runs recorded after the last cached activity.
                              Requires /process-recent to have run at least once.
                              Example:
                                curl -X POST http://localhost:8000/update-since-last

POST /update-by-date          Process all runs recorded on a specific date (UTC).
                              Body: {"date": "YYYY-MM-DD"}
                              Example:
                                curl -X POST http://localhost:8000/update-by-date \
                                     -H "Content-Type: application/json" \
                                     -d '{"date": "2024-05-15"}'
"""

import logging
from datetime import date

from fastapi import Body, FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.cache import load_last_processed, save_last_processed
from app.config import settings
from app.pipeline import run_pipeline
from app.strava.client import StravaClient

log = logging.getLogger(__name__)


class ProcessRequest(BaseModel):
    activity_id: int | None = None


class DateRequest(BaseModel):
    date: date


app = FastAPI(title="AI Running Assistant")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_strava_client() -> StravaClient:
    return StravaClient(
        settings.strava_client_id,
        settings.strava_client_secret,
        settings.strava_refresh_token,
    )


async def _process_and_cache(activity_id: int) -> dict:
    """Run the full pipeline for one activity and persist it to the cache."""
    activity = await run_pipeline(activity_id)
    save_last_processed(activity_id, activity["start_date_local"])
    return activity


async def _process_batch(activity_ids: list[int]) -> list[int]:
    """Process a list of activity IDs in order, skipping on error. Returns processed IDs."""
    processed = []
    for aid in activity_ids:
        try:
            await _process_and_cache(aid)
            processed.append(aid)
            log.info("Processed activity %s", aid)
        except Exception as exc:
            log.exception("Failed to process activity %s: %s", aid, exc)
    return processed


# ---------------------------------------------------------------------------
# Strava webhook
# ---------------------------------------------------------------------------

@app.get("/webhook/strava")
async def strava_verify(
    hub_challenge: str = Query(default=None, alias="hub.challenge"),
    hub_verify_token: str = Query(default=None, alias="hub.verify_token"),
):
    if hub_verify_token != settings.strava_verify_token:
        raise HTTPException(status_code=403, detail="Invalid verify token")
    return {"hub.challenge": hub_challenge}


@app.post("/webhook/strava")
async def strava_event(payload: dict):
    if payload.get("object_type") == "activity" and payload.get("aspect_type") == "create":
        if payload.get("owner_id") == settings.strava_athlete_id:
            await run_pipeline(payload["object_id"])
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Manual triggers
# ---------------------------------------------------------------------------

@app.post("/process-recent")
async def process_recent(body: ProcessRequest | None = Body(default=None)):
    if body and body.activity_id:
        activity_id = body.activity_id
    else:
        activity_id = _make_strava_client().get_latest_activity_id()

    await _process_and_cache(activity_id)
    return {"status": "ok", "activity_id": activity_id}


@app.post("/update-since-last")
async def update_since_last_processed_activity():
    cached = load_last_processed()
    if cached is None:
        raise HTTPException(
            status_code=400,
            detail="No cached activity — run /process-recent first.",
        )

    activity_ids = _make_strava_client().get_activities_since(cached["start_date_local"])
    activity_ids = [aid for aid in activity_ids if aid != cached["activity_id"]]

    if not activity_ids:
        return {"status": "ok", "processed": [], "message": "No new activities since last processed run."}

    processed = await _process_batch(activity_ids)
    return {"status": "ok", "processed": processed}


@app.post("/update-by-date")
async def update_by_date(body: DateRequest):
    activity_ids = _make_strava_client().get_activities_on_date(body.date)

    if not activity_ids:
        return {"status": "ok", "processed": [], "message": f"No run activities found on {body.date}."}

    processed = await _process_batch(activity_ids)
    return {"status": "ok", "processed": processed}
