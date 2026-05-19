# AI Running Assistant

Webhook-driven automation that analyses a completed Strava run against a training plan and sends the coach a WhatsApp summary via Claude AI.

## Pipeline
1. Strava webhook fires on activity completion
2. FastAPI fetches full activity data via stravalib
3. Google Sheets row is located by activity date
4. Claude analyses actual vs planned, writes result to column F
5. Coach receives analysis on WhatsApp via Meta Cloud API

## Sheet structure
- **A**: Day | **B**: Date (MM/DD/YYYY) | **C**: Session Type | **D**: Planned
- **E**: Athlete comments — **NEVER write here**
- **F**: Claude's analysis — write here only

Tabs follow pattern `{RunnerName}_{StartDate/EndDate}` (e.g., `Name_May5/15` or `Name_Apr28/May4`). Tab resolution is always dynamic via date range matching.

## Runner configuration
All runner-specific values in `.env` only — no hardcoded values:
- `RUNNER_NAME` — tab resolution
- `STRAVA_ATHLETE_ID` — webhook validation
- `COACH_WHATSAPP` — message destination
- `SPREADSHEET_ID` — training plan sheet
- `GOOGLE_CREDENTIALS_PATH` — service account JSON
- Strava, Anthropic, WhatsApp tokens

## Architecture
```
POST /webhook/strava → main.py (FastAPI)
                     → pipeline.py orchestrates:
                        ├─ strava/client.py          fetch activity + weather
                        ├─ sheets/client.py          read plan row, write col F
                        ├─ agents/running_coach.py   Claude analysis
                        └─ notifications/whatsapp.py send to coach
```

## Key constraints
- **Never write to column E** — athlete notes only
- **TDD**: tests written before implementation
- **Claude tone**: factual, no fluff, summary only
- **Dynamic tab resolution**: list all tabs, match date range — never construct names
- **No hardcoding**: all runner context from .env or sheet

## Tech stack
Python 3.11+, FastAPI, Uvicorn, Anthropic SDK (claude-sonnet-4-6), stravalib, Google Sheets API, Open-Meteo API (weather), Meta WhatsApp Cloud API, pytest, pytest-asyncio, pydantic-settings

## Endpoints
- `POST /webhook/strava` — Strava webhook (production)
- `GET /webhook/strava` — Strava challenge verification
- `POST /process-recent` — Manual trigger for testing (optional: `{"activity_id": 12345}`)

