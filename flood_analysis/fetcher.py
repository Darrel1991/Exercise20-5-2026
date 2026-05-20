"""
Fetches historical weather and river discharge data from Open-Meteo APIs.
No API key required.
"""

import logging
from datetime import date, timedelta

import requests

from flood_analysis.config import (
    ARCHIVE_API,
    FLOOD_API,
    WEATHER_VARIABLES,
    FLOOD_LOCATIONS,
)

logger = logging.getLogger(__name__)

# Open-Meteo allows max ~370 days per request for archive API.
# For multi-year queries we chunk into yearly requests.
_MAX_DAYS_PER_REQUEST = 365


def _chunk_date_range(start: date, end: date) -> list[tuple[date, date]]:
    """Split a date range into chunks of max _MAX_DAYS_PER_REQUEST days."""
    chunks = []
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + timedelta(days=_MAX_DAYS_PER_REQUEST - 1), end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)
    return chunks


def fetch_historical_weather(
    lat: float,
    lng: float,
    start_date: date,
    end_date: date,
) -> dict | None:
    """Fetch daily historical weather data from Open-Meteo Archive API.

    Returns dict with 'daily' key containing parallel arrays:
        time, precipitation_sum, rain_sum, precipitation_hours,
        temperature_2m_max, temperature_2m_min, et0_fao_evapotranspiration
    """
    all_daily = {var: [] for var in ["time"] + WEATHER_VARIABLES}

    for chunk_start, chunk_end in _chunk_date_range(start_date, end_date):
        params = {
            "latitude": lat,
            "longitude": lng,
            "start_date": chunk_start.isoformat(),
            "end_date": chunk_end.isoformat(),
            "daily": ",".join(WEATHER_VARIABLES),
            "timezone": "Asia/Kuala_Lumpur",
        }
        try:
            resp = requests.get(ARCHIVE_API, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            daily = data.get("daily", {})
            for key in all_daily:
                all_daily[key].extend(daily.get(key, []))
        except Exception:
            logger.exception(
                "Failed to fetch weather archive for %.2f,%.2f (%s to %s)",
                lat, lng, chunk_start, chunk_end,
            )
            return None

    return {
        "latitude": lat,
        "longitude": lng,
        "daily": all_daily,
    }


def fetch_historical_weather_for_location(
    location_key: str,
    start_date: date,
    end_date: date,
) -> dict | None:
    """Fetch historical weather for a named flood location.

    Returns enriched dict with location metadata + daily weather data.
    """
    loc = FLOOD_LOCATIONS.get(location_key)
    if not loc:
        logger.error("Unknown flood location: %s", location_key)
        return None

    result = fetch_historical_weather(loc["lat"], loc["lng"], start_date, end_date)
    if not result:
        return None

    result["location_key"] = location_key
    result["location_name"] = loc["name"]
    result["state"] = loc["state"]
    result["river"] = loc.get("river")
    return result


def fetch_river_discharge(
    lat: float,
    lng: float,
    past_days: int = 90,
    forecast_days: int = 30,
) -> dict | None:
    """Fetch river discharge data from Open-Meteo Flood API.

    Returns dict with daily river_discharge (m³/s) and
    river_discharge_mean/max for ensemble models.
    """
    params = {
        "latitude": lat,
        "longitude": lng,
        "daily": "river_discharge,river_discharge_mean,river_discharge_max",
        "past_days": past_days,
        "forecast_days": forecast_days,
    }
    try:
        resp = requests.get(FLOOD_API, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "daily": data.get("daily", {}),
        }
    except Exception:
        logger.exception(
            "Failed to fetch river discharge for %.2f,%.2f", lat, lng,
        )
        return None


def fetch_river_discharge_for_location(
    location_key: str,
    past_days: int = 90,
    forecast_days: int = 30,
) -> dict | None:
    """Fetch river discharge for a named flood location."""
    loc = FLOOD_LOCATIONS.get(location_key)
    if not loc:
        logger.error("Unknown flood location: %s", location_key)
        return None

    result = fetch_river_discharge(loc["lat"], loc["lng"], past_days, forecast_days)
    if not result:
        return None

    result["location_key"] = location_key
    result["location_name"] = loc["name"]
    result["state"] = loc["state"]
    result["river"] = loc.get("river")
    return result
