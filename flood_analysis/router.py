"""
FastAPI router for flood analysis endpoints.

All endpoints use Open-Meteo (no API key). Historical queries may take
a few seconds for multi-year date ranges.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from flood_analysis.config import FLOOD_LOCATIONS
from flood_analysis.fetcher import (
    fetch_historical_weather_for_location,
    fetch_historical_weather,
    fetch_river_discharge_for_location,
    fetch_river_discharge,
)
from flood_analysis.analyzer import analyze_flood_risk, compare_locations

router = APIRouter(prefix="/api/flood", tags=["flood-analysis"])


# ── Location listing ────────────────────────────────────────────────

@router.get("/locations")
def list_locations():
    """List all available flood monitoring locations."""
    locations = []
    for key, loc in FLOOD_LOCATIONS.items():
        locations.append({
            "key": key,
            "name": loc["name"],
            "state": loc["state"],
            "lat": loc["lat"],
            "lng": loc["lng"],
            "river": loc.get("river"),
        })
    return {"count": len(locations), "locations": locations}


# ── Historical weather ──────────────────────────────────────────────

@router.get("/history/{location_key}")
def get_flood_history(
    location_key: str,
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
):
    """Get historical daily precipitation data for a flood location.

    Example: /api/flood/history/kuala-krai?start=2021-01-01&end=2021-12-31
    """
    if location_key not in FLOOD_LOCATIONS:
        raise HTTPException(404, f"Unknown location: {location_key}. Use /api/flood/locations to see available keys.")

    end_date = end or date.today()
    if start > end_date:
        raise HTTPException(400, "start date must be before end date")

    data = fetch_historical_weather_for_location(location_key, start, end_date)
    if not data:
        raise HTTPException(502, "Failed to fetch data from Open-Meteo")

    return {
        "location_key": data["location_key"],
        "location_name": data["location_name"],
        "state": data["state"],
        "river": data.get("river"),
        "date_range": {"start": start.isoformat(), "end": end_date.isoformat()},
        "daily": data["daily"],
    }


# ── Flood risk analysis ────────────────────────────────────────────

@router.get("/analysis/{location_key}")
def get_flood_analysis(
    location_key: str,
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
):
    """Analyze historical flood risk for a location.

    Returns risk score, extreme events, consecutive rain periods,
    monthly/yearly breakdowns, and monsoon analysis.

    Example: /api/flood/analysis/kuala-krai?start=2021-01-01&end=2025-12-31
    """
    if location_key not in FLOOD_LOCATIONS:
        raise HTTPException(404, f"Unknown location: {location_key}")

    end_date = end or date.today()
    if start > end_date:
        raise HTTPException(400, "start date must be before end date")

    data = fetch_historical_weather_for_location(location_key, start, end_date)
    if not data:
        raise HTTPException(502, "Failed to fetch data from Open-Meteo")

    analysis = analyze_flood_risk(data["daily"])
    loc = FLOOD_LOCATIONS[location_key]

    return {
        "location_key": location_key,
        "location_name": loc["name"],
        "state": loc["state"],
        "river": loc.get("river"),
        "lat": loc["lat"],
        "lng": loc["lng"],
        **analysis,
    }


# ── River discharge ────────────────────────────────────────────────

@router.get("/river/{location_key}")
def get_river_discharge(
    location_key: str,
    past_days: int = Query(90, ge=1, le=365, description="Past days of discharge data"),
    forecast_days: int = Query(30, ge=1, le=210, description="Forecast days ahead"),
):
    """Get river discharge data (past + forecast) for a location.

    Uses Open-Meteo GloFAS river discharge model.
    Example: /api/flood/river/kuala-krai?past_days=90&forecast_days=30
    """
    if location_key not in FLOOD_LOCATIONS:
        raise HTTPException(404, f"Unknown location: {location_key}")

    data = fetch_river_discharge_for_location(location_key, past_days, forecast_days)
    if not data:
        raise HTTPException(502, "Failed to fetch river discharge data from Open-Meteo")

    loc = FLOOD_LOCATIONS[location_key]
    return {
        "location_key": location_key,
        "location_name": loc["name"],
        "state": loc["state"],
        "river": loc.get("river"),
        "lat": loc["lat"],
        "lng": loc["lng"],
        "daily": data["daily"],
    }


# ── Compare multiple locations ──────────────────────────────────────

@router.get("/compare")
def compare_flood_risk(
    locations: str = Query(
        ...,
        description="Comma-separated location keys (e.g. kuala-krai,kota-bharu,shah-alam)",
    ),
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
):
    """Compare flood risk across multiple locations.

    Example: /api/flood/compare?locations=kuala-krai,kota-bharu,shah-alam&start=2021-01-01
    """
    keys = [k.strip() for k in locations.split(",") if k.strip()]
    if len(keys) < 2:
        raise HTTPException(400, "Provide at least 2 comma-separated location keys")
    if len(keys) > 10:
        raise HTTPException(400, "Maximum 10 locations per comparison")

    for k in keys:
        if k not in FLOOD_LOCATIONS:
            raise HTTPException(404, f"Unknown location: {k}")

    end_date = end or date.today()
    results = []
    errors = []

    for key in keys:
        data = fetch_historical_weather_for_location(key, start, end_date)
        if not data:
            errors.append(key)
            continue

        analysis = analyze_flood_risk(data["daily"])
        results.append({
            "location_key": key,
            "location_name": FLOOD_LOCATIONS[key]["name"],
            "state": FLOOD_LOCATIONS[key]["state"],
            "analysis": analysis,
        })

    comparison = compare_locations(results)

    return {
        "date_range": {"start": start.isoformat(), "end": end_date.isoformat()},
        "count": len(comparison),
        "errors": errors if errors else None,
        "comparison": comparison,
    }


# ── Custom lat/lng query (not limited to preset locations) ─────────

@router.get("/custom")
def custom_location_analysis(
    lat: float = Query(..., ge=-10, le=20, description="Latitude"),
    lng: float = Query(..., ge=90, le=140, description="Longitude"),
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
):
    """Analyze flood risk for any custom lat/lng coordinate.

    Example: /api/flood/custom?lat=5.53&lng=102.20&start=2021-01-01
    """
    end_date = end or date.today()
    if start > end_date:
        raise HTTPException(400, "start date must be before end date")

    data = fetch_historical_weather(lat, lng, start, end_date)
    if not data:
        raise HTTPException(502, "Failed to fetch data from Open-Meteo")

    analysis = analyze_flood_risk(data["daily"])

    return {
        "lat": lat,
        "lng": lng,
        **analysis,
    }
