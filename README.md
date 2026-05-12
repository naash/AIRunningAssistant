# AI Running Assistant

Webhook-driven automation that analyses a completed Strava run against a training plan and delivers a coaching summary via WhatsApp — powered by Claude AI.

```
Strava activity completed
        │
        ▼
POST /webhook/strava  (FastAPI)
        │
        ├─ Fetch full activity from Strava API
        ├─ Locate today's row in Google Sheets training plan
        ├─ Claude analyses actual vs planned
        ├─ Write analysis to Sheet column F
        └─ Send coaching summary to WhatsApp
```

## What it does

When a run is completed on Strava, the app:

1. Pulls the full activity — distance, pace, splits, heart rate, elevation, cadence, power, effort scores
2. Finds the matching row in a Google Sheets training plan by date
3. Sends everything to Claude with the planned session and athlete notes
4. Writes Claude's analysis back to the sheet
5. Delivers the analysis to the coach over WhatsApp

The runner and all their credentials live entirely in `.env` — swapping to a different athlete is a single file change.

## Tech stack

| Layer | Technology |
|---|---|
| API server | FastAPI + Uvicorn |
| Strava data | stravalib |
| Training plan | Google Sheets API (service account) |
| AI analysis | Anthropic Claude (`claude-sonnet-4-6`) |
| Notifications | Meta WhatsApp Cloud API |
| Config | pydantic-settings |
| Tests | pytest + pytest-asyncio |

## Project structure

```
app/
├── main.py                  # FastAPI app — webhook + manual trigger endpoints
├── pipeline.py              # Orchestrates the full run-to-analysis flow
├── config.py                # Pydantic settings from .env
├── strava/
│   └── client.py            # OAuth token refresh, activity fetch, split normalisation
├── sheets/
│   └── client.py            # Dynamic tab resolution, row lookup, column F write
├── agents/
│   └── running_coach.py     # Claude prompt builder and analysis
└── notifications/
    └── whatsapp.py          # Meta Cloud API message sender
```

## Sheet structure

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Day | Date (MM/DD/YYYY) | Session Type | Planned | Athlete notes | **Claude analysis** |

Tabs follow the pattern `{StartDate/EndDate}` (e.g. `May5/15` or `Apr28/May4`). The app resolves the correct tab dynamically — never by constructing the name.

Column E (athlete notes) is read-only. The app only writes to column F.

## Getting started

### Prerequisites

- Python 3.11+
- Strava account with API app
- Google Cloud service account with Sheets API enabled
- Meta WhatsApp Business API account
- A public HTTPS URL for the webhook (e.g. [Railway](https://railway.app), [Render](https://render.com), or [ngrok](https://ngrok.com) for local dev)

### Setup

```bash
git clone https://github.com/YOUR_USERNAME/ai-running-assistant
cd ai-running-assistant
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` — see [SETUP.md](SETUP.md) for step-by-step credential instructions for Strava, Google Sheets, and WhatsApp.

### Run

```bash
python -m uvicorn app.main:app --reload
```

### Manual trigger (no webhook needed)

```bash
# Process most recent Strava activity
curl -X POST http://localhost:8000/process-recent

# Process a specific activity
curl -X POST http://localhost:8000/process-recent \
  -H "Content-Type: application/json" \
  -d '{"activity_id": 12345678}'
```

### Tests

```bash
pytest                          # unit tests
pytest -m integration           # hit real Google Sheets API (requires credentials)
```

## Configuration

All runner-specific values live in `.env`:

```
STRAVA_CLIENT_ID=
STRAVA_CLIENT_SECRET=
STRAVA_REFRESH_TOKEN=
STRAVA_ATHLETE_ID=
RUNNER_NAME=
RUNNER_WHATSAPP=
GOOGLE_CREDENTIALS_PATH=
SPREADSHEET_ID=
ANTHROPIC_API_KEY=
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
```

See `.env.example` for descriptions and [SETUP.md](SETUP.md) for how to obtain each value.

## Webhook registration

Once the server is deployed at a public URL:

```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=YOUR_CLIENT_ID \
  -d client_secret=YOUR_CLIENT_SECRET \
  -d callback_url=https://YOUR_DOMAIN/webhook/strava \
  -d verify_token=YOUR_STRAVA_VERIFY_TOKEN
```
