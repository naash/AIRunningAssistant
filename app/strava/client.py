from stravalib import Client


def _to_seconds(value) -> int:
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
            "total_elevation_gain": float(a.total_elevation_gain) if a.total_elevation_gain is not None else None,
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

            # Splits
            "splits_metric": _normalize_splits(a.splits_metric),
        }


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
