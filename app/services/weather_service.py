"""
Weather Service
---------------
Fetches weather data from the free Open-Meteo API.
No API key required.
"""

import httpx
from app.config import OPEN_METEO_BASE_URL


def get_weather(lat: float, lon: float) -> dict:
    """
    Get current + 7-day weather forecast for the given coordinates.

    Returns:
        {
            "current": {"temperature": float, "rainfall": float},
            "forecast": [
                {"date": str, "temperature": float, "rainfall": float},
                ...
            ]
        }
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,precipitation_sum",
        "forecast_days": 7,
        "timezone": "Asia/Kolkata",
    }

    response = httpx.get(OPEN_METEO_BASE_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    daily = data.get("daily", {})
    dates = daily.get("time", [])
    temps = daily.get("temperature_2m_max", [])
    rains = daily.get("precipitation_sum", [])

    forecast = []
    for i in range(len(dates)):
        forecast.append({
            "date": dates[i],
            "temperature": temps[i] if i < len(temps) else 0,
            "rainfall": rains[i] if i < len(rains) else 0,
        })

    current = {
        "temperature": temps[0] if temps else 0,
        "rainfall": rains[0] if rains else 0,
    }

    return {"current": current, "forecast": forecast}
