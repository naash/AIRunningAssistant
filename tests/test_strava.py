import pytest
from datetime import datetime, date, timedelta, timezone
from unittest.mock import MagicMock, patch
from app.strava.client import StravaClient, _sport_type_str, _RUN_SPORT_TYPES


def _make_summary_activity(activity_id: int, sport_type: str = "Run") -> MagicMock:
    a = MagicMock()
    a.id = activity_id
    a.sport_type = sport_type
    return a


def _make_relaxed_sport_type(root: str) -> MagicMock:
    """Simulate stravalib's RelaxedSportType(root='Run') wrapper."""
    m = MagicMock()
    m.root = root
    m.__str__ = lambda self: f"RelaxedSportType(root='{root}')"
    return m


class TestSportTypeStr:
    def test_plain_string_returned_as_is(self):
        a = MagicMock()
        a.sport_type = "Run"
        assert _sport_type_str(a) == "Run"

    def test_relaxed_sport_type_unwrapped_via_root(self):
        a = MagicMock()
        a.sport_type = _make_relaxed_sport_type("Run")
        assert _sport_type_str(a) == "Run"

    def test_relaxed_virtual_run_unwrapped(self):
        a = MagicMock()
        a.sport_type = _make_relaxed_sport_type("VirtualRun")
        assert _sport_type_str(a) == "VirtualRun"


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

    # Location
    a.start_latlng = MagicMock()
    a.start_latlng.lat = 45.5017
    a.start_latlng.lng = -122.6750

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
    "start_latlng",
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


class TestGetActivitiesSince:
    def test_calls_get_activities_with_after_param(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = []
        after = datetime(2026, 5, 10, 7, 0, 0)

        client.get_activities_since(after)

        mock_stravalib.get_activities.assert_called_once_with(after=after)

    def test_returns_run_ids_oldest_first(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = [
            _make_summary_activity(30, "Run"),
            _make_summary_activity(20, "Run"),
            _make_summary_activity(10, "Run"),
        ]

        result = client.get_activities_since(datetime(2026, 5, 1))

        assert result == [10, 20, 30]

    def test_filters_out_non_run_sport_types(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = [
            _make_summary_activity(1, "Ride"),
            _make_summary_activity(2, "Run"),
            _make_summary_activity(3, "Swim"),
            _make_summary_activity(4, "VirtualRun"),
        ]

        result = client.get_activities_since(datetime(2026, 5, 1))

        assert result == [4, 2]

    def test_includes_trail_run(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = [
            _make_summary_activity(5, "TrailRun"),
        ]

        result = client.get_activities_since(datetime(2026, 5, 1))

        assert result == [5]

    def test_excludes_activities_with_none_id(self, strava_client):
        client, mock_stravalib = strava_client
        a = _make_summary_activity(None, "Run")
        mock_stravalib.get_activities.return_value = [a]

        result = client.get_activities_since(datetime(2026, 5, 1))

        assert result == []

    def test_returns_empty_list_when_no_runs(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = []

        result = client.get_activities_since(datetime(2026, 5, 1))

        assert result == []


def _make_summary_activity_with_local_date(
    activity_id: int, local_date: date, sport_type: str = "Run", distance: float = 5000.0
) -> MagicMock:
    a = _make_summary_activity(activity_id, sport_type)
    a.start_date_local = datetime(local_date.year, local_date.month, local_date.day, 7, 0, 0)
    a.distance = distance
    return a


class TestGetActivitiesOnDate:
    def test_queries_with_one_day_padding_each_side(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = []

        client.get_activities_on_date(date(2026, 5, 15))

        mock_stravalib.get_activities.assert_called_once_with(
            after=datetime(2026, 5, 14, 0, 0, 0),
            before=datetime(2026, 5, 16, 23, 59, 59),
        )

    def test_returns_run_matching_local_date(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = [
            _make_summary_activity_with_local_date(99, date(2026, 5, 15), distance=5000.0),
        ]

        result = client.get_activities_on_date(date(2026, 5, 15))

        assert result == [{"id": 99, "distance": 5000.0}]

    def test_excludes_activities_on_adjacent_local_dates(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = [
            _make_summary_activity_with_local_date(1, date(2026, 5, 14)),
            _make_summary_activity_with_local_date(2, date(2026, 5, 15), distance=6000.0),
            _make_summary_activity_with_local_date(3, date(2026, 5, 16)),
        ]

        result = client.get_activities_on_date(date(2026, 5, 15))

        assert result == [{"id": 2, "distance": 6000.0}]

    def test_filters_non_run_sport_types(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = [
            _make_summary_activity_with_local_date(1, date(2026, 5, 15), "Ride"),
            _make_summary_activity_with_local_date(2, date(2026, 5, 15), "Run", distance=7000.0),
        ]

        result = client.get_activities_on_date(date(2026, 5, 15))

        assert result == [{"id": 2, "distance": 7000.0}]

    def test_returns_oldest_first(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = [
            _make_summary_activity_with_local_date(300, date(2026, 5, 15), distance=5000.0),
            _make_summary_activity_with_local_date(100, date(2026, 5, 15), distance=8000.0),
        ]

        result = client.get_activities_on_date(date(2026, 5, 15))

        assert result == [{"id": 100, "distance": 8000.0}, {"id": 300, "distance": 5000.0}]

    def test_returns_empty_when_no_runs_on_date(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = []

        result = client.get_activities_on_date(date(2026, 5, 15))

        assert result == []

    def test_strength_session_type_includes_weight_training(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = [
            _make_summary_activity_with_local_date(10, date(2026, 5, 15), "WeightTraining", distance=0.0),
            _make_summary_activity_with_local_date(11, date(2026, 5, 15), "Run", distance=5000.0),
        ]

        result = client.get_activities_on_date(date(2026, 5, 15), session_type="Strength")

        assert result == [{"id": 10, "distance": 0.0}]

    def test_running_session_type_excludes_weight_training(self, strava_client):
        client, mock_stravalib = strava_client
        mock_stravalib.get_activities.return_value = [
            _make_summary_activity_with_local_date(10, date(2026, 5, 15), "WeightTraining"),
            _make_summary_activity_with_local_date(11, date(2026, 5, 15), "Run", distance=5000.0),
        ]

        result = client.get_activities_on_date(date(2026, 5, 15), session_type="Running")

        assert result == [{"id": 11, "distance": 5000.0}]


class TestFindBestMatch:
    def test_returns_single_activity_regardless_of_distance(self):
        activities = [{"id": 1, "distance": 5000.0}]

        result = StravaClient.find_best_match(activities, 10.0)

        assert result == {"id": 1, "distance": 5000.0}

    def test_returns_first_when_no_planned_distance(self):
        activities = [{"id": 1, "distance": 5000.0}, {"id": 2, "distance": 10000.0}]

        result = StravaClient.find_best_match(activities, None)

        assert result == {"id": 1, "distance": 5000.0}

    def test_returns_closest_distance_match(self):
        activities = [{"id": 1, "distance": 5000.0}, {"id": 2, "distance": 10200.0}]

        result = StravaClient.find_best_match(activities, 10.0)

        assert result == {"id": 2, "distance": 10200.0}

    def test_picks_closer_among_multiple_activities(self):
        activities = [
            {"id": 1, "distance": 8000.0},
            {"id": 2, "distance": 10200.0},
            {"id": 3, "distance": 15000.0},
        ]

        result = StravaClient.find_best_match(activities, 10.0)

        assert result == {"id": 2, "distance": 10200.0}

    def test_raises_when_no_activities(self):
        with pytest.raises(ValueError):
            StravaClient.find_best_match([], 10.0)
