from fastapi import Body, FastAPI, HTTPException, Query
from pydantic import BaseModel
from app.config import settings
from app.pipeline import run_pipeline


class ProcessRequest(BaseModel):
    activity_id: int | None = None


app = FastAPI(title="AI Running Assistant")


@app.get("/webhook/strava")
async def strava_verify(
    hub_mode: str = Query(default=None, alias="hub.mode"),
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


@app.post("/process-recent")
async def process_recent(body: ProcessRequest | None = Body(default=None)):
    from app.strava.client import StravaClient

    if body and body.activity_id:
        activity_id = body.activity_id
    else:
        client = StravaClient(
            settings.strava_client_id,
            settings.strava_client_secret,
            settings.strava_refresh_token,
        )
        activity_id = client.get_latest_activity_id()

    await run_pipeline(activity_id)
    return {"status": "ok", "activity_id": activity_id}
