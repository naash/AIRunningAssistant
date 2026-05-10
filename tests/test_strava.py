import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import MagicMock, patch
from app.strava.client import StravaClient


def _quantity(value: float) -> MagicMock:
    q = MagicMock()
    q.__float__ = lambda _: value
    return q


def _make_mock_split(split_num, distance_m, moving_time_s, avg_speed_mps, elev_diff_m, avg_hr, pace_zone):
    s = MagicMock()
    s.split = split_num
    s.distance = _quantity(distance_m)
    s.moving_time = timedelta(seconds=moving_time_s)
    s.elapsed_time = timedelta(seconds=moving_time_s + 5)
    s.average_speed = _quantity(avg_speed_mps)
    s.elevation_difference = _quantity(elev_diff_m)
    s.average_heartrate = avg_hr
    s.pace_zone = pace_zone
    return s


def _make_mock_activity():
    a = MagicMock()

    # Identity
    a.id = 12345678
    a.name = "Morning Run"
    a.type = "Run"
    a.sport_type = "Run"
    a.description = "Easy recovery run around the park"
    a.workout_type = 0

    # Time
    a.start_date = datetime(2026, 5, 10, 7, 0, 0, tzinfo=timezone.utc)
    a.start_date_local = datetime(2026, 5, 10, 7, 0, 0)
    a.moving_time = timedelta(seconds=1860)
    a.elapsed_time = timedelta(seconds=1920)

    # Distance & speed (pint Quantities)
    a.distance = _quantity(5020.0)
    a.average_speed = _quantity(2.70)
    a.max_speed = _quantity(4.10)

    # Elevation (elev_high/elev_low are plain floats in stravalib, gain is pint)
    a.total_elevation_gain = _quantity(42.0)
    a.elev_high = 185.0
    a.elev_low = 143.0

    # Heart rate (plain floats/ints in stravalib)
    a.average_heartrate = None
    a.max_heartrate = None

    # Cadence, power, temp
    a.average_cadence = 85.5
    a.average_watts = None
    a.average_temp = 18

    # Effort
    a.calories = 312.0
    a.suffer_score = 32
    a.perceived_exertion = None

    # Splits
    a.splits_metric = [
        _make_mock_split(1, 1000.0, 372, 2.69, 5.0,  148.0, 2),
        _make_mock_split(2, 1000.0, 368, 2.72, -3.0, 150.0, 2),
        _make_mock_split(3, 1000.0, 370, 2.70, 8.0,  152.0, 2),
        _make_mock_split(4, 1000.0, 375, 2.67, -2.0, 151.0, 2),
        _make_mock_split(5,  20.0,   7,  2.86,  0.0, 149.0, 2),
    ]

    return a


@pytest.fixture
def strava_client():
    with patch("app.strava.client.Client") as mock_class:
        mock_stravalib = MagicMock()
        mock_class.return_value = mock_stravalib
        mock_stravalib.refresh_access_token.return_value = {"access_token": "fresh_token"}
        client = StravaClient("cid", "csecret", "rtoken")
        client._stravalib = mock_stravalib
        yield client, mock_stravalib


EXPECTED_KEYS = {
    "id", "name", "type", "sport_type", "description", "workout_type",
    "start_date", "start_date_local",
    "distance", "moving_time", "elapsed_time",
    "average_speed", "max_speed",
    "total_elevation_gain", "elev_high", "elev_low",
    "average_heartrate", "max_heartrate",
    "average_cadence", "average_watts",
    "calories", "suffer_score", "perceived_exertion", "average_temp",
    "splits_metric",
}


class TestStravaClientInit:
    def test_refreshes_token_on_init(self):
        with patch("app.strava.client.Client") as mock_class:
            mock_stravalib = MagicMock()
            mock_class.return_value = mock_stravalib
            mock_stravalib.refresh_access_token.return_value = {"access_token": "fresh_token"}

            StravaClient("cid", "csecret", "rtoken")

            mock_stravalib.refresh_access_token.assert_called_once_with(
                client_id="cid",
                client_secret="csecret",
                refresh_token="rtoken",
            )

    def test_sets_access_token_after_refresh(self):
        with patch("app.strava.client.Client") as mock_class:
            mock_stravalib = MagicMock()
            mock_class.return_value = mock_stravalib
            mock_stravalib.refresh_access_token.return_value = {"access_token": "fresh_token"}

            StravaClient("cid", "csecret", "rtoken")

            assert mock_stravalib.access_token == "fresh_token"


class TestGetActivity:
    def test_calls_stravalib_with_activity_id(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        client.get_activity(12345678)

        mock_stravalib.get_activity.assert_called_once_with(12345678)

    def test_returns_dict(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result, dict)

    def test_returns_expected_keys(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert set(result.keys()) == EXPECTED_KEYS

    # --- Time & identity ---

    def test_start_date_is_date_object(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result["start_date"], date)
        assert result["start_date"] == date(2026, 5, 10)

    def test_start_date_local_is_datetime(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result["start_date_local"], datetime)
        assert result["start_date_local"] == datetime(2026, 5, 10, 7, 0, 0)

    def test_moving_time_is_int_seconds(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result["moving_time"], int)
        assert result["moving_time"] == 1860

    def test_elapsed_time_is_int_seconds(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result["elapsed_time"], int)
        assert result["elapsed_time"] == 1920

    def test_workout_type_is_int(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["workout_type"] == 0

    # --- Distance & speed ---

    def test_distance_is_float_in_meters(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result["distance"], float)
        assert result["distance"] == 5020.0

    def test_average_speed_is_float(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result["average_speed"], float)
        assert result["average_speed"] == pytest.approx(2.70)

    def test_max_speed_is_float(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result["max_speed"], float)
        assert result["max_speed"] == pytest.approx(4.10)

    # --- Elevation ---

    def test_total_elevation_gain_is_float(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result["total_elevation_gain"], float)
        assert result["total_elevation_gain"] == pytest.approx(42.0)

    def test_elev_high_is_float(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["elev_high"] == 185.0

    def test_elev_low_is_float(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["elev_low"] == 143.0

    def test_elevation_fields_can_be_none(self, strava_client):
        client, mock_stravalib = strava_client
        activity = _make_mock_activity()
        activity.elev_high = None
        activity.elev_low = None
        activity.total_elevation_gain = None
        mock_stravalib.get_activity.return_value = activity

        result = client.get_activity(12345678)

        assert result["elev_high"] is None
        assert result["elev_low"] is None
        assert result["total_elevation_gain"] is None

    # --- Heart rate ---

    def test_average_heartrate_can_be_none(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["average_heartrate"] is None

    def test_average_heartrate_when_present(self, strava_client):
        client, mock_stravalib = strava_client
        activity = _make_mock_activity()
        activity.average_heartrate = 152.0
        mock_stravalib.get_activity.return_value = activity

        result = client.get_activity(12345678)

        assert result["average_heartrate"] == 152.0

    def test_max_heartrate_can_be_none(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["max_heartrate"] is None

    def test_max_heartrate_when_present(self, strava_client):
        client, mock_stravalib = strava_client
        activity = _make_mock_activity()
        activity.max_heartrate = 178
        mock_stravalib.get_activity.return_value = activity

        result = client.get_activity(12345678)

        assert result["max_heartrate"] == 178

    # --- Cadence, power, environment ---

    def test_average_cadence_when_present(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["average_cadence"] == 85.5

    def test_average_cadence_can_be_none(self, strava_client):
        client, mock_stravalib = strava_client
        activity = _make_mock_activity()
        activity.average_cadence = None
        mock_stravalib.get_activity.return_value = activity

        result = client.get_activity(12345678)

        assert result["average_cadence"] is None

    def test_average_watts_can_be_none(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["average_watts"] is None

    def test_average_watts_when_present(self, strava_client):
        client, mock_stravalib = strava_client
        activity = _make_mock_activity()
        activity.average_watts = 245.0
        mock_stravalib.get_activity.return_value = activity

        result = client.get_activity(12345678)

        assert result["average_watts"] == 245.0

    def test_average_temp_when_present(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["average_temp"] == 18

    # --- Effort ---

    def test_calories_when_present(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["calories"] == 312.0

    def test_suffer_score_when_present(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["suffer_score"] == 32

    def test_perceived_exertion_can_be_none(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["perceived_exertion"] is None

    def test_perceived_exertion_when_present(self, strava_client):
        client, mock_stravalib = strava_client
        activity = _make_mock_activity()
        activity.perceived_exertion = 5
        mock_stravalib.get_activity.return_value = activity

        result = client.get_activity(12345678)

        assert result["perceived_exertion"] == 5

    # --- Splits ---

    def test_splits_metric_is_list(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert isinstance(result["splits_metric"], list)
        assert len(result["splits_metric"]) == 5

    def test_splits_metric_each_is_dict(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        for split in result["splits_metric"]:
            assert isinstance(split, dict)

    def test_splits_metric_keys(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert set(result["splits_metric"][0].keys()) == {
            "split", "distance", "moving_time", "elapsed_time",
            "average_speed", "elevation_difference", "average_heartrate", "pace_zone",
        }

    def test_splits_metric_distance_is_float(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["splits_metric"][0]["distance"] == 1000.0
        assert isinstance(result["splits_metric"][0]["distance"], float)

    def test_splits_metric_moving_time_is_int_seconds(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activity.return_value = _make_mock_activity()

        result = client.get_activity(12345678)

        assert result["splits_metric"][0]["moving_time"] == 372
        assert isinstance(result["splits_metric"][0]["moving_time"], int)

    def test_splits_metric_can_be_none(self, strava_client):
        client, mock_stravalib = strava_client
        activity = _make_mock_activity()
        activity.splits_metric = None
        mock_stravalib.get_activity.return_value = activity

        result = client.get_activity(12345678)

        assert result["splits_metric"] is None
