from datetime import date, datetime, timedelta

from stravalib import Client


def _to_seconds(value) -> int:
    if hasattr(value, "total_seconds"):
        return int(value.total_seconds())
    return int(value)


class StravaClient:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._stravalib = Client()
        token = self._stravalib.refresh_access_token(
            client_id=client_id,
            client_secret=client_secret,
            refresh_token=refresh_token,
        )
        self._stravalib.access_token = token["access_token"]

    def get_latest_activity_id(self) -> int:
        activities = list(self._stravalib.get_activities(limit=1))
        if not activities:
            raise ValueError("No activities found")
        return activities[0].id

    def get_activities_since(self, after: datetime) -> list[int]:
        """Return run activity IDs recorded after *after* (UTC), oldest first."""
        activities = list(self._stravalib.get_activities(after=after))
        return _filter_runs(activities, reverse=True)

    def get_activities_on_date(self, on_date: date) -> list[int]:
        """Return run activity IDs whose local date matches *on_date*, oldest first.

        Queries ±1 day around the target date to cover any UTC offset, then
        filters by start_date_local so only activities that actually fell on
        *on_date* in the athlete's local time are returned.
        """
        after = datetime(on_date.year, on_date.month, on_date.day, 0, 0, 0) - timedelta(days=1)
        before = datetime(on_date.year, on_date.month, on_date.day, 23, 59, 59) + timedelta(days=1)
        activities = list(self._stravalib.get_activities(after=after, before=before))
        matching = [
            a for a in activities
            if _sport_type_str(a) in _RUN_SPORT_TYPES
            and a.start_date_local is not None
            and a.start_date_local.date() == on_date
        ]
        return [a.id for a in reversed(matching) if a.id is not None]

    def get_activity(self, activity_id: int) -> dict:
        a = self._stravalib.get_activity(activity_id)
        return {
            # Identity
            "id": a.id,
            "name": a.name,
            "type": str(a.type),
            "sport_type": str(a.sport_type),
            "description": a.description,
            "workout_type": a.workout_type,
            # Time
            "start_date": a.start_date.date(),
            "start_date_local": a.start_date_local,
            "moving_time": _to_seconds(a.moving_time),
            "elapsed_time": _to_seconds(a.elapsed_time),
            # Distance & speed
            "distance": float(a.distance),
            "average_speed": float(a.average_speed),
            "max_speed": float(a.max_speed) if a.max_speed is not None else None,
            # Elevation
            "total_elevation_gain": float(a.total_elevation_gain)
            if a.total_elevation_gain is not None
            else None,
            "elev_high": a.elev_high,
            "elev_low": a.elev_low,
            # Heart rate
            "average_heartrate": a.average_heartrate,
            "max_heartrate": a.max_heartrate,
            # Cadence & power
            "average_cadence": a.average_cadence,
            "average_watts": a.average_watts,
            # Environment & effort
            "average_temp": a.average_temp,
            "calories": a.calories,
            "suffer_score": a.suffer_score,
            "perceived_exertion": a.perceived_exertion,
            # Location
            "start_latlng": [float(a.start_latlng.lat), float(a.start_latlng.lon)] if a.start_latlng else None,
            # Splits
            "splits_metric": _normalize_splits(a.splits_metric),
        }


_RUN_SPORT_TYPES = {"Run", "VirtualRun", "TrailRun"}


def _sport_type_str(activity) -> str:
    """Extract a plain string from stravalib's sport_type field.

    Newer stravalib versions wrap sport_type in a RelaxedSportType model
    (e.g. RelaxedSportType(root='Run')). Unwrap via .root when present.
    """
    st = activity.sport_type
    return str(st.root) if hasattr(st, "root") else str(st)


def _filter_runs(activities: list, reverse: bool = False) -> list[int]:
    runs = [a for a in activities if _sport_type_str(a) in _RUN_SPORT_TYPES]
    if reverse:
        runs = list(reversed(runs))
    return [a.id for a in runs if a.id is not None]


def _normalize_splits(splits) -> list | None:
    if splits is None:
        return None
    return [
        {
            "split": s.split,
            "distance": float(s.distance),
            "moving_time": _to_seconds(s.moving_time),
            "elapsed_time": _to_seconds(s.elapsed_time),
            "average_speed": float(s.average_speed),
            "elevation_difference": float(s.elevation_difference),
            "average_heartrate": s.average_heartrate,
            "pace_zone": s.pace_zone,
        }
        for s in splits
    ]
