# AI Running Assistant

Webhook-driven automation that analyses a completed Strava run against a training plan and sends the coach a WhatsApp summary via Claude AI.

## Pipeline (in order)
1. Strava fires a webhook when a run is completed
2. FastAPI fetches full activity data via stravalib
3. Google Sheets row is located for the runner by activity date
4. Claude analyses actual vs planned, writes result to column F
5. Coach receives the analysis on WhatsApp via Meta Cloud API

## Sheet structure
- **A**: Day | **B**: Date (MM/DD/YYYY) | **C**: Session Type | **D**: Planned distance/session
- **E**: Athlete comments — **NEVER write here under any circumstances**
- **F**: Claude's analysis — write here only

### Tab naming convention
Tabs follow the pattern `{RunnerName}_{MonthStartDate/EndDate}`:
- Same month: `Name_May5/15`
- Cross-month: `Name_Apr28/May4`

Tab resolution is always dynamic: list all tabs and find the one whose date range contains the activity date. Never construct the tab name from scratch.

## Runner configuration
All runner-specific values live exclusively in `.env` — nothing is hardcoded in source code or docs:
- `RUNNER_NAME` — used for tab resolution
- `STRAVA_ATHLETE_ID` — used to validate incoming webhook events
- `RUNNER_WHATSAPP` — destination number for coach messages
- `SPREADSHEET_ID` — Google Sheet containing the training plan

Swapping to a different runner means updating `.env` only.

## Architecture
```
POST /webhook/strava
        │
   main.py (FastAPI)
        │
   pipeline.py  ──── strava/client.py          fetch activity
                ──── sheets/client.py          read plan row, write col F
                ──── agents/running_coach.py   Claude analysis
                └─── notifications/whatsapp.py send to coach
```

## Key constraints
- **Never write to column E** — that belongs to the athlete
- **TDD**: tests are written before implementation, always
- **Claude analysis tone**: factual, no fluff, summary only
- All runner context (name, goal, target) comes from the sheet — nothing hardcoded

## Tech stack
- Python 3.11+, FastAPI, Uvicorn
- Anthropic Python SDK — model `claude-sonnet-4-6`
- stravalib
- google-api-python-client + google-auth
- Meta WhatsApp Cloud API (via httpx)
- pytest, pytest-asyncio

## Development
```bash
pip install -r requirements.txt
cp .env.example .env  # fill in credentials (see SETUP.md)
uvicorn app.main:app --reload
```

```bash
pytest
```
