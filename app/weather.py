import httpx
from datetime import datetime


async def get_weather(start_latlng: list | None, start_date_local: datetime) -> dict | None:
    """
    Fetch historical weather from Open-Meteo API (no API key required).
    Returns dict with temp_c, humidity_pct, windspeed_kmh, or None if unavailable.
    """
    if not start_latlng:
        return None

    lat, lng = start_latlng
    date_str = start_date_local.date().isoformat()
    hour = start_date_local.hour

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lng,
                    "hourly": "temperature_2m,relativehumidity_2m,windspeed_10m",
                    "start_date": date_str,
                    "end_date": date_str,
                    "timezone": "auto",
                },
                timeout=5,
            )
            if response.status_code != 200:
                return None

            data = response.json()
            hourly = data.get("hourly", {})
            temps = hourly.get("temperature_2m", [])
            humidity = hourly.get("relativehumidity_2m", [])
            windspeed = hourly.get("windspeed_10m", [])

            if hour < len(temps) and hour < len(humidity) and hour < len(windspeed):
                return {
                    "temp_c": temps[hour],
                    "humidity_pct": humidity[hour],
                    "windspeed_kmh": windspeed[hour],
                }
            return None

    except Exception:
        return None
