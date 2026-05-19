import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from app.weather import get_weather


@pytest.mark.asyncio
async def test_get_weather_success():
    """Test successful weather fetch with correct hour index selection."""
    start_latlng = [45.5017, -122.6750]  # Portland
    start_date_local = datetime(2026, 5, 12, 14, 30)  # 2:30 PM

    mock_response = {
        "hourly": {
            "temperature_2m": [10, 12, 14, 16, 18, 20, 22, 24, 25, 26, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14],
            "relativehumidity_2m": [80, 75, 70, 65, 60, 55, 50, 45, 40, 35, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95],
            "windspeed_10m": [5, 4, 3, 2, 1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        }
    }

    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = mock_response

    with patch("app.weather.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_http_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await get_weather(start_latlng, start_date_local)

    assert result is not None
    assert result["temp_c"] == 23  # Hour 14 (index 14 = 23°C)
    assert result["humidity_pct"] == 50  # Hour 14 (index 14 = 50%)
    assert result["windspeed_kmh"] == 9  # Hour 14 (index 14 = 9 km/h)


@pytest.mark.asyncio
async def test_get_weather_correct_url_params():
    """Test that correct URL and params are built from coordinates and date."""
    start_latlng = [40.7128, -74.0060]  # NYC
    start_date_local = datetime(2026, 5, 15, 10, 0)

    mock_response = {
        "hourly": {
            "temperature_2m": [15] * 24,
            "relativehumidity_2m": [60] * 24,
            "windspeed_10m": [8] * 24,
        }
    }

    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = mock_response

    with patch("app.weather.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_http_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        await get_weather(start_latlng, start_date_local)

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "https://api.open-meteo.com/v1/forecast" in call_args[0]
        params = call_args[1]["params"]
        assert params["latitude"] == 40.7128
        assert params["longitude"] == -74.0060
        assert params["start_date"] == "2026-05-15"
        assert params["end_date"] == "2026-05-15"


@pytest.mark.asyncio
async def test_get_weather_none_coordinates():
    """Test returns None gracefully when coordinates are None."""
    result = await get_weather(None, datetime(2026, 5, 12, 10, 0))
    assert result is None


@pytest.mark.asyncio
async def test_get_weather_api_error():
    """Test returns None gracefully when API returns non-200."""
    start_latlng = [45.5017, -122.6750]
    start_date_local = datetime(2026, 5, 12, 10, 0)

    mock_http_response = MagicMock()
    mock_http_response.status_code = 503

    with patch("app.weather.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_http_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await get_weather(start_latlng, start_date_local)

    assert result is None


@pytest.mark.asyncio
async def test_get_weather_exception_handling():
    """Test returns None gracefully when API request raises exception."""
    start_latlng = [45.5017, -122.6750]
    start_date_local = datetime(2026, 5, 12, 10, 0)

    with patch("app.weather.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await get_weather(start_latlng, start_date_local)

    assert result is None


@pytest.mark.asyncio
async def test_get_weather_hour_out_of_range():
    """Test returns None when hour index is out of range in response."""
    start_latlng = [45.5017, -122.6750]
    start_date_local = datetime(2026, 5, 12, 23, 0)  # 11 PM

    mock_response = {
        "hourly": {
            "temperature_2m": [10] * 10,  # Only 10 hours, hour 23 is out of range
            "relativehumidity_2m": [60] * 10,
            "windspeed_10m": [5] * 10,
        }
    }

    mock_http_response = MagicMock()
    mock_http_response.status_code = 200
    mock_http_response.json.return_value = mock_response

    with patch("app.weather.httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_http_response)
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client_class.return_value.__aexit__ = AsyncMock(return_value=None)

        result = await get_weather(start_latlng, start_date_local)

    assert result is None
