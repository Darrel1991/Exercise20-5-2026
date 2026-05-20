from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.connection import get_db
from db.models import WeatherForecast, WeatherWarning, Earthquake

router = APIRouter(prefix="/api/weather", tags=["weather"])


# ── Forecasts ────────────────────────────────────────────────────────

@router.get("/forecast")
def get_forecasts(
    date_filter: Optional[date] = Query(None, alias="date"),
    location: Optional[str] = Query(None, description="location_id or location_name"),
    db: Session = Depends(get_db),
):
    """Get weather forecasts, optionally filtered by date and location."""
    q = db.query(WeatherForecast)

    if date_filter:
        q = q.filter(WeatherForecast.date == date_filter)
    else:
        # Default: today's forecast
        q = q.filter(WeatherForecast.date >= date.today())

    if location:
        q = q.filter(
            (WeatherForecast.location_id == location)
            | (WeatherForecast.location_name.contains(location))
        )

    forecasts = q.order_by(WeatherForecast.date, WeatherForecast.location_name).all()

    return {
        "count": len(forecasts),
        "forecasts": [
            {
                "location_id": f.location_id,
                "location_name": f.location_name,
                "date": f.date.isoformat() if f.date else None,
                "morning_forecast": f.morning_forecast,
                "afternoon_forecast": f.afternoon_forecast,
                "night_forecast": f.night_forecast,
                "summary_forecast": f.summary_forecast,
                "summary_when": f.summary_when,
                "min_temp": f.min_temp,
                "max_temp": f.max_temp,
                "latitude": f.latitude,
                "longitude": f.longitude,
            }
            for f in forecasts
        ],
    }


@router.get("/forecast/map")
def get_forecast_map(
    date_filter: Optional[date] = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
    """Forecasts with coordinates for map rendering — only districts with lat/lng."""
    target_date = date_filter or date.today()
    forecasts = (
        db.query(WeatherForecast)
        .filter(
            WeatherForecast.date == target_date,
            WeatherForecast.latitude.isnot(None),
            WeatherForecast.longitude.isnot(None),
        )
        .all()
    )

    return {
        "date": target_date.isoformat(),
        "count": len(forecasts),
        "points": [
            {
                "location_id": f.location_id,
                "location_name": f.location_name,
                "lat": f.latitude,
                "lng": f.longitude,
                "summary": f.summary_forecast,
                "min_temp": f.min_temp,
                "max_temp": f.max_temp,
                "morning": f.morning_forecast,
                "afternoon": f.afternoon_forecast,
                "night": f.night_forecast,
            }
            for f in forecasts
        ],
    }


# ── Warnings ─────────────────────────────────────────────────────────

@router.get("/warnings")
def get_warnings(
    active_only: bool = Query(True, description="Only show currently active warnings"),
    db: Session = Depends(get_db),
):
    """Get weather warnings."""
    q = db.query(WeatherWarning)

    if active_only:
        now = datetime.utcnow()
        q = q.filter(
            (WeatherWarning.valid_to >= now) | (WeatherWarning.valid_to.is_(None))
        )

    warnings = q.order_by(desc(WeatherWarning.issued)).all()

    return {
        "count": len(warnings),
        "warnings": [
            {
                "id": w.id,
                "title_en": w.title_en,
                "title_bm": w.title_bm,
                "heading_en": w.heading_en,
                "text_en": w.text_en,
                "text_bm": w.text_bm,
                "instruction_en": w.instruction_en,
                "issued": w.issued.isoformat() if w.issued else None,
                "valid_from": w.valid_from.isoformat() if w.valid_from else None,
                "valid_to": w.valid_to.isoformat() if w.valid_to else None,
                "boundary": {
                    "lat_min": w.boundary_lat_min,
                    "lat_max": w.boundary_lat_max,
                    "lng_min": w.boundary_lng_min,
                    "lng_max": w.boundary_lng_max,
                } if w.boundary_lat_min is not None else None,
            }
            for w in warnings
        ],
    }


# ── Earthquakes ──────────────────────────────────────────────────────

@router.get("/earthquakes")
def get_earthquakes(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Get recent earthquakes."""
    quakes = (
        db.query(Earthquake)
        .order_by(desc(Earthquake.timestamp))
        .limit(limit)
        .all()
    )

    return {
        "count": len(quakes),
        "earthquakes": [
            {
                "id": q.id,
                "location": q.location,
                "latitude": q.latitude,
                "longitude": q.longitude,
                "magnitude": q.magnitude,
                "depth": q.depth,
                "timestamp": q.timestamp.isoformat() if q.timestamp else None,
            }
            for q in quakes
        ],
    }
