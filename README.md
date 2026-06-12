# AI Running Assistant

Webhook-driven system that analyses a completed Strava activity against a training plan and delivers a coaching summary to WhatsApp — fully automated, sub-30 seconds from activity save to message received.

Training coaches work across multiple athletes, each with their own plan, session schedule, and quirks. After every session, someone has to pull the data, compare it to the plan, and write up feedback. This system automates that loop entirely. When an athlete finishes a run or strength session, it intercepts the Strava webhook, locates the correct row in a Google Sheets training plan, sends the full activity data to Claude for analysis, writes the result back to the sheet, and pushes a coaching summary to WhatsApp. The non-trivial part is reliably matching the right Strava activity to the right row in the plan when an athlete logs two sessions on the same day — or when the activity that arrived isn't the one the plan expected.

---

## Architecture

```
Strava activity completed
        │
        ▼
POST /webhook/strava  (FastAPI on Railway)
        │
        ▼
Route to runner by owner_id  ──  RunnerRegistry (O(1) lookup)
        │
        ▼
Activity matching
  ├─ Resolve training plan tab by date range  (dynamic — never hardcoded)
  ├─ Read planned session: type (col C) + distance (col E)
  ├─ Fetch candidate activities from Strava  (±1 day UTC window)
  ├─ Filter by session type  (Running → Run/VirtualRun/TrailRun, Strength → WeightTraining)
  └─ Pick best match: closest actual distance to planned distance
        │
        ▼
Google Sheets  — read full row  (planned session, athlete notes)
        │
        ▼
Claude  (claude-sonnet-4-6, 512 tokens)
  — actual vs planned: distance, pace, splits, HR, cadence, effort, weather
        │
        ├──▶ Google Sheets  — write analysis to col G
        └──▶ WhatsApp  — coaching summary delivered to coach
```

**FastAPI** receives Strava's push notification and immediately returns 200. All pipeline work runs asynchronously after the response, within the same process.

**Activity matching** is the core logic. A single date can have a morning run and an evening strength session, or two runs at different distances. The system reads the planned session from the sheet first, uses the session type to filter to the right Strava sport category, then picks the candidate whose actual distance is closest to the planned distance.

**Google Sheets** is both the input (training plan) and output (analysis). Tabs are named by date range (`May5/15`, `Apr28/May4`) and resolved dynamically — the app lists all tabs, parses each one's date range, and matches by date. No tab name is ever constructed or hardcoded.

**Claude** receives a structured prompt: planned vs actual metrics, per-km splits, heart rate, cadence, elevation, and weather at the start location. The system prompt is configurable per-runner to include VDOT, HR zones, and injury context. Output is capped at 512 tokens — factual, no padding.

**Weather** is fetched from Open-Meteo at the activity's GPS coordinates and injected into the prompt. Warm weather flags are added automatically to contextualise elevated HR.

---

## Key design decisions

### Multi-runner architecture

Runners are defined in `runners.json` (gitignored), each entry carrying a `display_name`, `strava_athlete_id`, and `spreadsheet_id`. At startup, `RunnerRegistry` builds two lookup tables — by name (for manual API calls) and by athlete ID (for webhook routing). Webhook dispatch is O(1). Adding a second runner is one JSON entry; no code changes required.

Each runner owns a separate Google Sheet. This isolates training data completely and means there's no shared tab namespace to manage. Per-runner caches live at `data/{name}/last_processed.json`, so backfill operations on one runner can't affect another.

### Activity matching

The naive approach — take the most recent Strava activity — breaks the moment an athlete logs two sessions in a day. Taking all activities and processing each also breaks: a morning run and an evening strength session on the same date should hit different rows in the plan.

The fix: read the planned session from the sheet *first*. Extract session type (col C) and planned distance (col E). Use session type to filter Strava's activity list to the right sport category. If one match remains, use it. If multiple, pick the one whose actual distance is closest to the planned. This handles every realistic case — double run days, mixed-type days, and sessions where the athlete ran slightly more or less than planned.

### Google credentials via env var

`from_service_account_file` requires a file on disk, which doesn't survive ephemeral cloud deployments. `SheetsClient` takes the credentials as a JSON string and calls `from_service_account_info(json.loads(...))` instead. The full credentials blob lives in `GOOGLE_CREDENTIALS_JSON` as a single minified line in `.env`. The same pattern applies to the runner registry via `RUNNERS_CONFIG` — every piece of configuration that varies between environments is an env var, so Railway deployment is just a variable swap with no repo changes.

### Agent design

A single Claude call covers everything: the planned session, full activity metrics, per-km splits, effort scores, and contextual weather. A separate summariser or a chain of calls would add latency and cost for no benefit at this scale. The system prompt accepts a per-runner profile string (VDOT, HR zones, injury history) injected at call time, so the same agent class serves every runner. Max 512 tokens enforces brevity — the output is a coaching note, not an essay.

### Deployment

Railway runs the app as an always-on persistent process. This matters for webhooks: Strava fires immediately after an activity is saved, and a cold-start delay on a serverless platform causes the webhook to time out, triggering retries and duplicate processing. A persistent process eliminates this. The `Procfile` is a single line; everything else is env vars.

---

## Tech stack

| Layer | Technology |
|---|---|
| API server | FastAPI + Uvicorn |
| Strava data | stravalib |
| Training plan | Google Sheets API (service account) |
| Weather | Open-Meteo API |
| AI analysis | Anthropic Claude (`claude-sonnet-4-6`) |
| Notifications | Meta WhatsApp Cloud API |
| Config | pydantic-settings |
| Deployment | Railway |
| Tests | pytest + pytest-asyncio |

---

## Project structure

```
app/
├── main.py                  # FastAPI endpoints — webhook handler and manual triggers
├── pipeline.py              # Orchestrates the full activity-to-analysis flow
├── config.py                # RunnerConfig, RunnerRegistry, pydantic Settings
├── cache.py                 # Persists last processed activity per runner to disk
├── weather.py               # Open-Meteo fetch at activity GPS coordinates
├── strava/
│   └── client.py            # Token refresh, activity fetch, best-match selection
├── sheets/
│   └── client.py            # Dynamic tab resolution, row lookup, col G write
├── agents/
│   └── running_coach.py     # Prompt builder, Claude call, pace/split formatters
└── notifications/
    └── whatsapp.py          # Meta Cloud API outbound message

runners.json                      # Runner registry — gitignored, contains athlete IDs
runners/{name}.md                 # Per-runner profile: VDOT, HR zones, injury history
data/{name}/last_processed.json   # Cache: last processed activity ID + datetime per runner
```

---

## Endpoints

All manual endpoints require `runner_name` in the request body. The webhook routes by Strava `owner_id` automatically.

| Endpoint | When to use |
|---|---|
| `POST /webhook/strava` | Strava push notification — production entry point |
| `GET /webhook/strava` | Strava challenge verification during webhook registration |
| `POST /process-recent` | Process the runner's most recent Strava activity |
| `POST /update-by-date` | Find and process the best-matching activity for a specific date |
| `POST /update-since-last` | Process all new activities since the last cached one |

```powershell
# Process most recent activity
Invoke-RestMethod -Method Post http://localhost:8000/process-recent `
    -ContentType 'application/json' `
    -Body '{"runner_name": "nishant"}'

# Process a specific activity by ID
Invoke-RestMethod -Method Post http://localhost:8000/process-recent `
    -ContentType 'application/json' `
    -Body '{"runner_name": "nishant", "activity_id": 12345678}'

# Process best-matching activity for a given date
Invoke-RestMethod -Method Post http://localhost:8000/update-by-date `
    -ContentType 'application/json' `
    -Body '{"runner_name": "nishant", "date": "2026-05-15"}'

# Catch up on all new activities since last processed
Invoke-RestMethod -Method Post http://localhost:8000/update-since-last `
    -ContentType 'application/json' `
    -Body '{"runner_name": "nishant"}'
```

---

## Setup

**Prerequisites:** Python 3.11+, Strava API app, Google Cloud service account with Sheets API enabled, Meta WhatsApp Business account, public HTTPS URL for the webhook.

```bash
git clone https://github.com/YOUR_USERNAME/ai-running-assistant
cd ai-running-assistant
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env` — see [SETUP.md](SETUP.md) for step-by-step credential instructions. For Railway, set all `.env` values as environment variables in the dashboard; no file deployment needed.

```bash
python -m uvicorn app.main:app --reload  # local dev

pytest                   # unit tests — no external calls
pytest -m integration    # hits real Google Sheets API
```

---

## What's next

- **Postgres persistence** — replace the JSON file cache with a proper activity history, enabling trend queries and cross-session analysis
- **WhatsApp inbound chatbot** — coach sends a WhatsApp message to query metrics or request a summary across any athlete
- **Weekly digest + pre-run briefing** — scheduled agents that push a week-in-review each Sunday and a session preview the night before a key workout
- **Prompt evals framework** — systematic evaluation of analysis quality against a labelled set of sessions, to catch regressions when the prompt or model changes
