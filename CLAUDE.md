# AI Running Assistant

Webhook-driven automation that analyses a completed Strava run against a training plan and sends the coach a WhatsApp summary via Claude AI.

## Pipeline
1. Strava webhook fires on activity completion
2. FastAPI fetches full activity data via stravalib
3. Google Sheets row is located by activity date
4. Claude analyses actual vs planned, writes result to column G
5. Coach receives analysis on WhatsApp via Meta Cloud API

## Sheet structure
- **A**: Day | **B**: Date (MM/DD/YYYY) | **C**: Session Type | **D**: Planned | **E**: Distance in km
- **F**: Athlete comments — **NEVER write here**
- **G**: AI Comments — write here only

Session Type values: `Running`, `Strength`, or leave blank. Used to filter matching Strava activities.

Tabs follow pattern `{StartDate/EndDate}` (e.g., `May5/15` or `Apr28/May4`). Tab resolution is always dynamic via date range matching — never construct tab names manually.

## Runner configuration
Runners are defined in `runners.json` (gitignored). Each entry requires:
- `display_name` — used for tab lookup and WhatsApp messages
- `strava_athlete_id` — used to route incoming webhooks to the correct runner
- `spreadsheet_id` — the runner's training plan sheet

Runner profile (VDOT, HR zones, tendencies, injury history, coach notes) lives in `runners/{name}.md` and is injected into every Claude analysis.

Shared credentials live in `.env`: Strava OAuth, Google service account path, Anthropic API key, WhatsApp token and `WHATSAPP_COACH_NUMBER`.

## Architecture
```
POST /webhook/strava  → main.py (FastAPI)
                      → pipeline.py orchestrates:
                         ├─ strava/client.py          fetch + best-match activity
                         ├─ weather.py                fetch weather at start location
                         ├─ sheets/client.py          read plan row, write col G
                         ├─ agents/running_coach.py   Claude analysis (runner profile injected)
                         └─ notifications/whatsapp.py send to coach

cache.py  — persists last processed activity_id + datetime to data/{runner_name}/last_processed.json
```

## Key constraints
- **Never write to columns E or F** — athlete data only
- **TDD**: tests written before implementation
- **Claude tone**: factual, no fluff, summary only
- **Dynamic tab resolution**: list all tabs, match date range — never construct names
- **Activity matching**: when processing by date, session type (col C) and planned distance (col E) are used to find the best-matching Strava activity

## Tech stack
Python 3.11+, FastAPI, Uvicorn, Anthropic SDK (claude-sonnet-4-6), stravalib, Google Sheets API, Open-Meteo API (weather), Meta WhatsApp Cloud API, pytest, pytest-asyncio, pydantic-settings

## Endpoints
All manual endpoints require `runner_name` in the request body.

- `POST /webhook/strava` — Strava push notification; routes by athlete ID (production)
- `GET /webhook/strava` — Strava challenge verification
- `POST /process-recent` — Process one activity. Body: `{"runner_name": "alice"}` or add `"activity_id"` to target a specific one
- `POST /update-since-last` — Process all runs since the last cached activity. Body: `{"runner_name": "alice"}`
- `POST /update-by-date` — Find and process the best-matching activity for the given date. Body: `{"runner_name": "alice", "date": "YYYY-MM-DD"}`
