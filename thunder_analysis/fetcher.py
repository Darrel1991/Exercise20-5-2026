"""
Fetches historical HOURLY weather data from Open-Meteo for
thunderstorm analysis at train stations.

Uses historical-forecast-api which provides model-detected thunderstorm
codes (WMO 95/96/99) and CAPE values for Malaysia (2022+).
Falls back to standard archive API for dates before 2022.
"""

import logging
from datetime import date, timedelta

import requests

from thunder_analysis.config import (
    ARCHIVE_API,
    HOURLY_VARIABLES,
    TRAIN_STATIONS,
)

# Historical forecast API — provides CAPE + real thunderstorm codes for Malaysia (2022+)
HIST_FORECAST_API = "https://historical-forecast-api.open-meteo.com/v1/forecast"
HIST_FORECAST_MIN_DATE = date(2022, 1, 1)

logger = logging.getLogger(__name__)

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


def _fetch_chunk(api_url: str, lat: float, lng: float,
                 chunk_start: date, chunk_end: date, variables: list) -> dict | None:
    """Fetch one chunk of hourly data from the given API endpoint."""
    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": chunk_start.isoformat(),
        "end_date": chunk_end.isoformat(),
        "hourly": ",".join(variables),
        "timezone": "Asia/Kuala_Lumpur",
    }
    try:
        resp = requests.get(api_url, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json().get("hourly", {})
    except Exception:
        logger.exception("Failed chunk %s %s-%s @ %.4f,%.4f",
                         api_url, chunk_start, chunk_end, lat, lng)
        return None


def fetch_hourly_weather(
    lat: float,
    lng: float,
    start_date: date,
    end_date: date,
) -> dict | None:
    """Fetch hourly historical weather data.

    Uses historical-forecast-api for dates >= 2022-01-01 (real CAPE +
    thunderstorm codes). Falls back to archive API for older dates
    (no CAPE/thunderstorm codes but has rain+gust).
    """
    all_hourly = {var: [] for var in ["time"] + HOURLY_VARIABLES}

    for chunk_start, chunk_end in _chunk_date_range(start_date, end_date):
        # Choose API per chunk: historical-forecast for 2022+, archive for older
        if chunk_start >= HIST_FORECAST_MIN_DATE:
            api_url = HIST_FORECAST_API
            variables = HOURLY_VARIABLES
        else:
            api_url = ARCHIVE_API
            # Archive does not support 'cape' for Malaysia — exclude it
            variables = [v for v in HOURLY_VARIABLES if v != "cape"]
            # If chunk straddles boundary, split it
            if chunk_end >= HIST_FORECAST_MIN_DATE:
                pre = _fetch_chunk(ARCHIVE_API, lat, lng, chunk_start,
                                   HIST_FORECAST_MIN_DATE - timedelta(days=1), variables)
                post = _fetch_chunk(HIST_FORECAST_API, lat, lng,
                                    HIST_FORECAST_MIN_DATE, chunk_end, HOURLY_VARIABLES)
                if pre is None or post is None:
                    return None
                # Merge pre (no cape) + post
                for key in all_hourly:
                    all_hourly[key].extend(pre.get(key, [None] * len(pre.get("time", []))))
                    all_hourly[key].extend(post.get(key, []))
                continue

        hourly = _fetch_chunk(api_url, lat, lng, chunk_start, chunk_end, variables)
        if hourly is None:
            return None
        n = len(hourly.get("time", []))
        for key in all_hourly:
            if key in hourly:
                all_hourly[key].extend(hourly[key])
            else:
                # Fill missing variable (e.g. cape for archive) with Nones
                all_hourly[key].extend([None] * n)

    return {"latitude": lat, "longitude": lng, "hourly": all_hourly}


def fetch_hourly_for_station(
    station_key: str,
    start_date: date,
    end_date: date,
) -> dict | None:
    """Fetch hourly historical weather for a named train station."""
    station = TRAIN_STATIONS.get(station_key)
    if not station:
        logger.error("Unknown train station: %s", station_key)
        return None

    result = fetch_hourly_weather(station["lat"], station["lng"], start_date, end_date)
    if not result:
        return None

    result["station_key"] = station_key
    result["station_name"] = station["name"]
    return result


# ── Forecast API ─────────────────────────────────────────────────────

FORECAST_API = "https://api.open-meteo.com/v1/forecast"

FORECAST_DAILY_VARIABLES = [
    "weathercode",
    "precipitation_sum",
    "rain_sum",
    "wind_gusts_10m_max",
    "precipitation_hours",
    "precipitation_probability_max",
    "temperature_2m_max",
    "temperature_2m_min",
    "cape_max",
]


def fetch_forecast(lat: float, lng: float, days: int = 16) -> dict | None:
    """Fetch daily weather forecast from Open-Meteo Forecast API."""
    params = {
        "latitude": lat,
        "longitude": lng,
        "daily": ",".join(FORECAST_DAILY_VARIABLES),
        "forecast_days": days,
        "timezone": "Asia/Kuala_Lumpur",
    }
    try:
        resp = requests.get(FORECAST_API, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {"latitude": lat, "longitude": lng, "daily": data.get("daily", {})}
    except Exception:
        logger.exception("Failed to fetch forecast for %.4f,%.4f", lat, lng)
        return None


def fetch_hourly_forecast(lat: float, lng: float, days: int = 16) -> dict | None:
    """Fetch hourly forecast data from Open-Meteo Forecast API (includes CAPE)."""
    hourly_vars = list(HOURLY_VARIABLES) + ["cape"]
    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": ",".join(hourly_vars),
        "forecast_days": days,
        "timezone": "Asia/Kuala_Lumpur",
    }
    try:
        resp = requests.get(FORECAST_API, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return {"hourly": data.get("hourly", {})}
    except Exception:
        logger.exception("Failed to fetch hourly forecast for %.4f,%.4f", lat, lng)
        return None
