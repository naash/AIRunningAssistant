from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

ACTIVITY_ID = 12345678
ACTIVITY_ID_2 = 99999999

SAMPLE_ACTIVITY = {
    "id": ACTIVITY_ID,
    "start_date_local": datetime(2026, 5, 10, 7, 0, 0),
}
CACHED = {
    "activity_id": ACTIVITY_ID,
    "start_date_local": datetime(2026, 5, 10, 7, 0, 0),
}


@pytest.fixture
async def http_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def mock_pipeline():
    with patch("app.main.run_pipeline", new_callable=AsyncMock) as mock:
        mock.return_value = SAMPLE_ACTIVITY
        yield mock


@pytest.fixture
def mock_strava():
    mock_client = MagicMock()
    mock_client.get_latest_activity_id.return_value = ACTIVITY_ID
    mock_client.get_activities_since.return_value = []
    mock_client.get_activities_on_date.return_value = []
    with patch("app.main.StravaClient") as mock_cls:
        mock_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_cache_fns():
    with patch("app.main.save_last_processed") as mock_save, \
         patch("app.main.load_last_processed") as mock_load:
        mock_load.return_value = CACHED
        yield mock_save, mock_load


# ---------------------------------------------------------------------------
# Strava webhook
# ---------------------------------------------------------------------------

class TestStravaWebhookVerify:
    async def test_returns_challenge_with_valid_token(self, http_client):
        response = await http_client.get(
            "/webhook/strava",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "abc123",
                "hub.verify_token": settings.strava_verify_token,
            },
        )

        assert response.status_code == 200
        assert response.json() == {"hub.challenge": "abc123"}

    async def test_rejects_invalid_verify_token(self, http_client):
        response = await http_client.get(
            "/webhook/strava",
            params={
                "hub.mode": "subscribe",
                "hub.challenge": "abc123",
                "hub.verify_token": "wrong_token",
            },
        )

        assert response.status_code == 403


class TestStravaWebhookEvent:
    async def test_triggers_pipeline_for_new_activity(self, http_client, mock_pipeline):
        response = await http_client.post(
            "/webhook/strava",
            json={
                "object_type": "activity",
                "aspect_type": "create",
                "owner_id": settings.strava_athlete_id,
                "object_id": ACTIVITY_ID,
            },
        )

        assert response.status_code == 200
        mock_pipeline.assert_awaited_once_with(ACTIVITY_ID)

    async def test_ignores_wrong_owner(self, http_client, mock_pipeline):
        response = await http_client.post(
            "/webhook/strava",
            json={
                "object_type": "activity",
                "aspect_type": "create",
                "owner_id": 0,
                "object_id": ACTIVITY_ID,
            },
        )

        assert response.status_code == 200
        mock_pipeline.assert_not_awaited()

    async def test_ignores_non_create_event(self, http_client, mock_pipeline):
        response = await http_client.post(
            "/webhook/strava",
            json={
                "object_type": "activity",
                "aspect_type": "update",
                "owner_id": settings.strava_athlete_id,
                "object_id": ACTIVITY_ID,
            },
        )

        assert response.status_code == 200
        mock_pipeline.assert_not_awaited()

    async def test_ignores_non_activity_object(self, http_client, mock_pipeline):
        response = await http_client.post(
            "/webhook/strava",
            json={
                "object_type": "athlete",
                "aspect_type": "create",
                "owner_id": settings.strava_athlete_id,
                "object_id": ACTIVITY_ID,
            },
        )

        assert response.status_code == 200
        mock_pipeline.assert_not_awaited()

    async def test_always_returns_ok_status(self, http_client, mock_pipeline):
        response = await http_client.post("/webhook/strava", json={})

        assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /process-recent
# ---------------------------------------------------------------------------

class TestProcessRecent:
    async def test_uses_latest_activity_when_no_body(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        await http_client.post("/process-recent")

        mock_strava.get_latest_activity_id.assert_called_once()
        mock_pipeline.assert_awaited_once_with(ACTIVITY_ID)

    async def test_uses_provided_activity_id(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        await http_client.post("/process-recent", json={"activity_id": ACTIVITY_ID_2})

        mock_pipeline.assert_awaited_once_with(ACTIVITY_ID_2)
        mock_strava.get_latest_activity_id.assert_not_called()

    async def test_returns_activity_id_in_response(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        response = await http_client.post("/process-recent")

        assert response.json()["activity_id"] == ACTIVITY_ID

    async def test_saves_cache_after_pipeline(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        mock_save, _ = mock_cache_fns
        await http_client.post("/process-recent")

        mock_save.assert_called_once_with(ACTIVITY_ID, SAMPLE_ACTIVITY["start_date_local"])

    async def test_returns_ok_status(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        response = await http_client.post("/process-recent")

        assert response.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# /update-since-last
# ---------------------------------------------------------------------------

class TestUpdateSinceLast:
    async def test_returns_400_when_no_cache(self, http_client, mock_pipeline, mock_strava):
        with patch("app.main.load_last_processed", return_value=None):
            response = await http_client.post("/update-since-last")

        assert response.status_code == 400

    async def test_fetches_since_cached_datetime(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        await http_client.post("/update-since-last")

        mock_strava.get_activities_since.assert_called_once_with(CACHED["start_date_local"])

    async def test_excludes_already_processed_activity(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        mock_strava.get_activities_since.return_value = [ACTIVITY_ID]

        await http_client.post("/update-since-last")

        mock_pipeline.assert_not_awaited()

    async def test_processes_new_activities(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        mock_strava.get_activities_since.return_value = [ACTIVITY_ID, ACTIVITY_ID_2]

        await http_client.post("/update-since-last")

        mock_pipeline.assert_awaited_once_with(ACTIVITY_ID_2)

    async def test_returns_processed_ids(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        mock_strava.get_activities_since.return_value = [ACTIVITY_ID, ACTIVITY_ID_2]
        mock_pipeline.return_value = {
            "id": ACTIVITY_ID_2,
            "start_date_local": datetime(2026, 5, 11, 7, 0, 0),
        }

        response = await http_client.post("/update-since-last")

        assert ACTIVITY_ID_2 in response.json()["processed"]

    async def test_returns_empty_when_no_new_activities(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        mock_strava.get_activities_since.return_value = []

        response = await http_client.post("/update-since-last")

        assert response.json()["processed"] == []
        mock_pipeline.assert_not_awaited()

    async def test_continues_processing_after_pipeline_failure(
        self, http_client, mock_strava, mock_cache_fns
    ):
        mock_strava.get_activities_since.return_value = [ACTIVITY_ID_2, 11111111]
        side_effects = [
            Exception("pipeline failed"),
            {"id": 11111111, "start_date_local": datetime(2026, 5, 12, 7, 0, 0)},
        ]
        with patch("app.main.run_pipeline", new_callable=AsyncMock, side_effect=side_effects):
            response = await http_client.post("/update-since-last")

        assert 11111111 in response.json()["processed"]
        assert ACTIVITY_ID_2 not in response.json()["processed"]


# ---------------------------------------------------------------------------
# /update-by-date
# ---------------------------------------------------------------------------

class TestUpdateByDate:
    async def test_fetches_activities_for_given_date(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        await http_client.post("/update-by-date", json={"date": "2026-05-15"})

        from datetime import date
        mock_strava.get_activities_on_date.assert_called_once_with(date(2026, 5, 15))

    async def test_processes_found_activities(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        mock_strava.get_activities_on_date.return_value = [ACTIVITY_ID]

        await http_client.post("/update-by-date", json={"date": "2026-05-15"})

        mock_pipeline.assert_awaited_once_with(ACTIVITY_ID)

    async def test_returns_processed_ids(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        mock_strava.get_activities_on_date.return_value = [ACTIVITY_ID]

        response = await http_client.post("/update-by-date", json={"date": "2026-05-15"})

        assert ACTIVITY_ID in response.json()["processed"]

    async def test_returns_empty_when_no_activities_on_date(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        mock_strava.get_activities_on_date.return_value = []

        response = await http_client.post("/update-by-date", json={"date": "2026-05-15"})

        assert response.json()["processed"] == []
        mock_pipeline.assert_not_awaited()

    async def test_returns_ok_status(
        self, http_client, mock_pipeline, mock_strava, mock_cache_fns
    ):
        response = await http_client.post("/update-by-date", json={"date": "2026-05-15"})

        assert response.json()["status"] == "ok"
