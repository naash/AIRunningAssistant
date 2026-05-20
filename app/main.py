"""
Endpoints
---------
POST /webhook/strava          Strava push notification handler (production use).
GET  /webhook/strava          Strava webhook subscription verification.

POST /process-recent          Process one activity and cache it.
                              Body: {"runner_name": "alice", "activity_id": 12345}
                              Omit activity_id to process the runner's most recent activity.
                              Example:
                                Invoke-RestMethod -Method Post http://localhost:8000/process-recent `
                                    -ContentType 'application/json' `
                                    -Body '{"runner_name": "alice"}'

POST /update-since-last       Process all runs recorded after the last cached activity.
                              Body: {"runner_name": "alice"}
                              Requires /process-recent to have run at least once.
                              Example:
                                Invoke-RestMethod -Method Post http://localhost:8000/update-since-last `
                                    -ContentType 'application/json' `
                                    -Body '{"runner_name": "alice"}'

POST /update-by-date          Process all runs recorded on a specific date.
                              Body: {"runner_name": "alice", "date": "YYYY-MM-DD"}
                              Example:
                                Invoke-RestMethod -Method Post http://localhost:8000/update-by-date `
                                    -ContentType 'application/json' `
                                    -Body '{"runner_name": "alice", "date": "2026-05-15"}'
"""

import logging
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from app.cache import load_last_processed, save_last_processed
from app.config import RunnerConfig, RunnerRegistry, settings
from app.pipeline import run_pipeline
from app.strava.client import StravaClient

log = logging.getLogger(__name__)

_RUNNERS_JSON = Path(__file__).parent.parent / "runners.json"

try:
    registry = RunnerRegistry.load(_RUNNERS_JSON)
except FileNotFoundError:
    registry = RunnerRegistry({})


class ProcessRequest(BaseModel):
    runner_name: str
    activity_id: int | None = None


class BatchRequest(BaseModel):
    runner_name: str


class DateRequest(BaseModel):
    runner_name: str
    date: date


app = FastAPI(title="AI Running Assistant")

def _get_runner(name: str) -> RunnerConfig:
    try:
        return registry.get_by_name(name)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Runner '{name}' not found.")


def _make_strava_client() -> StravaClient:
    return StravaClient(
        settings.strava_client_id,
        settings.strava_client_secret,
        settings.strava_refresh_token,
    )


async def _process_and_cache(activity_id: int, runner: RunnerConfig) -> dict:
    """Run the full pipeline for one activity and persist it to the cache."""
    activity = await run_pipeline(activity_id, runner)
    save_last_processed(runner.name, activity_id, activity["start_date_local"])
    return activity


async def _process_batch(activity_ids: list[int], runner: RunnerConfig) -> list[int]:
    """Process a list of activity IDs in order, skipping on error. Returns processed IDs."""
    processed = []
    for aid in activity_ids:
        try:
            await _process_and_cache(aid, runner)
            processed.append(aid)
            log.info("Processed activity %s", aid)
        except Exception as exc:
            log.exception("Failed to process activity %s: %s", aid, exc)
    return processed

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
        runner = registry.get_by_athlete_id(payload.get("owner_id"))
        if runner is not None:
            await run_pipeline(payload["object_id"], runner)
    return {"status": "ok"}

@app.post("/process-recent")
async def process_recent(body: ProcessRequest):
    runner = _get_runner(body.runner_name)
    activity_id = body.activity_id or _make_strava_client().get_latest_activity_id()
    await _process_and_cache(activity_id, runner)
    return {"status": "ok", "activity_id": activity_id}

@app.post("/update-since-last")
async def update_since_last_processed_activity(body: BatchRequest):
    runner = _get_runner(body.runner_name)
    cached = load_last_processed(runner.name)
    if cached is None:
        raise HTTPException(
            status_code=400,
            detail="No cached activity — run /process-recent first.",
        )

    activity_ids = _make_strava_client().get_activities_since(cached["start_date_local"])
    activity_ids = [aid for aid in activity_ids if aid != cached["activity_id"]]

    if not activity_ids:
        return {"status": "ok", "processed": [], "message": "No new activities since last processed run."}

    processed = await _process_batch(activity_ids, runner)
    return {"status": "ok", "processed": processed}

@app.post("/update-by-date")
async def update_by_date(body: DateRequest):
    runner = _get_runner(body.runner_name)
    activity_ids = _make_strava_client().get_activities_on_date(body.date)

    if not activity_ids:
        return {"status": "ok", "processed": [], "message": f"No run activities found on {body.date}."}

    processed = await _process_batch(activity_ids, runner)
    return {"status": "ok", "processed": processed}
