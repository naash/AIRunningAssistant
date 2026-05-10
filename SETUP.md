# Setup Guide

## Prerequisites
- Python 3.11+
- A public URL for the Strava webhook (use [ngrok](https://ngrok.com) for local dev)
- A Strava account with at least one activity
- A Google account with the training spreadsheet
- A Meta WhatsApp Business API account

---

## 1. Strava API App

1. Go to https://www.strava.com/settings/api
2. Create an application — note the **Client ID** and **Client Secret**
3. Set `Authorization Callback Domain` to your domain (or `localhost` for dev)

### Get your refresh token (one-time OAuth flow)
```bash
# Step 1 — open this URL in a browser, replacing CLIENT_ID
https://www.strava.com/oauth/authorize?client_id=CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all

# Step 2 — after approving, copy the `code` param from the redirect URL

# Step 3 — exchange for tokens
curl -X POST https://www.strava.com/oauth/token \
  -d client_id=CLIENT_ID \
  -d client_secret=CLIENT_SECRET \
  -d code=CODE_FROM_STEP_2 \
  -d grant_type=authorization_code
```
Save the `refresh_token` from the response — it does not expire unless revoked.

### Register the webhook
```bash
curl -X POST https://www.strava.com/api/v3/push_subscriptions \
  -d client_id=CLIENT_ID \
  -d client_secret=CLIENT_SECRET \
  -d callback_url=https://YOUR_PUBLIC_URL/webhook/strava \
  -d verify_token=ANY_SECRET_STRING_YOU_CHOOSE
```
Use the same `verify_token` value in your `.env`.

---

## 2. Google Sheets (Service Account)

1. Go to https://console.cloud.google.com
2. Create a project → enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → generate a JSON key → download it as `credentials.json`
4. Copy `credentials.json` to the project root
5. Share your training spreadsheet with the service account email (Editor access)

---

## 3. WhatsApp Business API (Meta)

1. Go to https://developers.facebook.com → create an app → add **WhatsApp** product
2. Under WhatsApp → API Setup, note your **Phone Number ID** and generate a **temporary access token** (or configure a permanent system user token)
3. Add a test phone number to receive messages

---

## 4. Environment variables

```bash
cp .env.example .env
```

Fill in all values in `.env` — see `.env.example` for the full list.

---

## 5. Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload

# In another terminal, expose your local server
ngrok http 8000
```

Update the Strava webhook `callback_url` with the ngrok HTTPS URL if it changes.
