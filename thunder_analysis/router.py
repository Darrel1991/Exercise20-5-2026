"""
FastAPI router for thunderstorm analysis endpoints.

Uses ERA5 HOURLY data with calibrated thunderstorm detection
aligned with the Open-Meteo forecast model's WMO classification.
"""

from datetime import date

from fastapi import APIRouter, Query, HTTPException

from thunder_analysis.config import TRAIN_STATIONS, TRAIN_LINES
from thunder_analysis.fetcher import (
    fetch_hourly_for_station,
    fetch_hourly_weather,
    fetch_forecast,
    fetch_hourly_forecast,
)
from thunder_analysis.analyzer import analyze_thunderstorm_risk, compare_stations

router = APIRouter(prefix="/api/thunder", tags=["thunder-analysis"])


@router.get("/stations")
def list_stations():
    """List all train lines and their stations."""
    lines = {}
    for line_key, line_info in TRAIN_LINES.items():
        line_stations = []
        for sk in line_info["stations"]:
            s = TRAIN_STATIONS.get(sk)
            if s:
                line_stations.append({
                    "key": sk,
                    "name": s["name"],
                    "lat": s["lat"],
                    "lng": s["lng"],
                    "line": line_key,
                })
        lines[line_key] = {
            "name": line_info["name"],
            "color": line_info["color"],
            "stations": line_stations,
        }
    return {"lines": lines}


@router.get("/analysis/{station_key}")
def get_station_analysis(
    station_key: str,
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
):
    """Analyze thunderstorm risk for a train station using hourly data.

    Uses ERA5-calibrated thunderstorm detection thresholds.
    """
    if station_key not in TRAIN_STATIONS:
        raise HTTPException(404, f"Unknown station: {station_key}")

    end_date = end or date.today()
    if start > end_date:
        raise HTTPException(400, "start date must be before end date")

    data = fetch_hourly_for_station(station_key, start, end_date)
    if not data:
        raise HTTPException(502, "Failed to fetch hourly data from Open-Meteo")

    analysis = analyze_thunderstorm_risk(data["hourly"])
    s = TRAIN_STATIONS[station_key]

    return {
        "station_key": station_key,
        "station_name": s["name"],
        "lat": s["lat"],
        "lng": s["lng"],
        **analysis,
    }


@router.get("/compare")
def compare_station_risk(
    stations: str = Query(
        None,
        description="Comma-separated station keys. Omit to compare all stations.",
    ),
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
):
    """Compare thunderstorm risk across stations using hourly data."""
    end_date = end or date.today()

    if stations:
        keys = [k.strip() for k in stations.split(",") if k.strip()]
    else:
        keys = list(TRAIN_STATIONS.keys())

    for k in keys:
        if k not in TRAIN_STATIONS:
            raise HTTPException(404, f"Unknown station: {k}")

    results = []
    errors = []

    for key in keys:
        data = fetch_hourly_for_station(key, start, end_date)
        if not data:
            errors.append(key)
            continue

        analysis = analyze_thunderstorm_risk(data["hourly"])
        results.append({
            "station_key": key,
            "station_name": TRAIN_STATIONS[key]["name"],
            "analysis": analysis,
        })

    comparison = compare_stations(results)

    return {
        "date_range": {"start": start.isoformat(), "end": end_date.isoformat()},
        "count": len(comparison),
        "errors": errors if errors else None,
        "comparison": comparison,
    }


@router.get("/daily/{station_key}")
def get_station_daily(
    station_key: str,
    year: int = Query(..., description="Year (YYYY)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
):
    """Get pre-computed daily rows for a station/month.

    Returns the SAME data the heatmap uses — one row per day with
    storm_hours, wmo_thunder_hours, max_cape, status, etc.
    """
    if station_key not in TRAIN_STATIONS:
        raise HTTPException(404, f"Unknown station: {station_key}")

    from datetime import date as date_type
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    start = date_type(year, month, 1)
    end = date_type(year, month, last_day)
    today = date_type.today()
    if end > today:
        end = today
    if start > today:
        return {"station_key": station_key, "year": year, "month": month, "days": []}

    data = fetch_hourly_for_station(station_key, start, end)
    if not data:
        raise HTTPException(502, "Failed to fetch hourly data")

    hourly = data["hourly"]
    times = hourly.get("time", [])
    rain_arr = hourly.get("rain", [])
    gust_arr = hourly.get("wind_gusts_10m", [])
    code_arr = hourly.get("weathercode", [])
    cape_arr = hourly.get("cape", [])

    from thunder_analysis.config import (
        WMO_THUNDER_CODES, THUNDER_RAIN_ONLY, THUNDER_RAIN_COMBO,
        THUNDER_GUST_COMBO, THUNDER_GUST_ONLY, CAPE_LIGHTNING,
    )

    per_day = {}
    for i in range(len(times)):
        dk = times[i][:10]
        r = rain_arr[i] if i < len(rain_arr) and rain_arr[i] is not None else 0.0
        g = gust_arr[i] if i < len(gust_arr) and gust_arr[i] is not None else 0.0
        wc = code_arr[i] if i < len(code_arr) and code_arr[i] is not None else 0
        cape = cape_arr[i] if i < len(cape_arr) and cape_arr[i] is not None else 0.0

        d = per_day.setdefault(dk, {
            "storm_hours": 0, "wmo_thunder_hours": 0, "lightning_hours": 0,
            "total_rain_mm": 0.0, "max_rain_mmh": 0.0,
            "max_gust_kmh": 0.0, "max_cape": 0.0,
        })
        d["total_rain_mm"] += r
        if r > d["max_rain_mmh"]: d["max_rain_mmh"] = r
        if g > d["max_gust_kmh"]: d["max_gust_kmh"] = g
        if cape > d["max_cape"]: d["max_cape"] = cape
        if wc in WMO_THUNDER_CODES:
            d["wmo_thunder_hours"] += 1
        if cape >= CAPE_LIGHTNING:
            d["lightning_hours"] += 1

        is_storm = (
            wc in WMO_THUNDER_CODES
            or r >= THUNDER_RAIN_ONLY
            or (r >= THUNDER_RAIN_COMBO and g >= THUNDER_GUST_COMBO)
            or g >= THUNDER_GUST_ONLY
        )
        if is_storm:
            d["storm_hours"] += 1

    days = []
    for dk in sorted(per_day.keys()):
        d = per_day[dk]
        if d["wmo_thunder_hours"] > 0:
            status = "THUNDERSTORM"
        elif d["storm_hours"] > 0:
            status = "STORM"
        elif d["max_rain_mmh"] >= 5:
            status = "HEAVY"
        else:
            status = "CLEAR"
        days.append({
            "date": dk,
            "storm_hours": d["storm_hours"],
            "wmo_thunder_hours": d["wmo_thunder_hours"],
            "lightning_hours": d["lightning_hours"],
            "total_rain_mm": round(d["total_rain_mm"], 1),
            "max_rain_mmh": round(d["max_rain_mmh"], 1),
            "max_gust_kmh": round(d["max_gust_kmh"], 1),
            "max_cape": round(d["max_cape"], 0),
            "status": status,
        })

    return {
        "station_key": station_key,
        "station_name": TRAIN_STATIONS[station_key]["name"],
        "year": year,
        "month": month,
        "days": days,
    }


@router.get("/hourly/{station_key}")
def get_station_hourly(
    station_key: str,
    date_str: str = Query(..., alias="date", description="Date (YYYY-MM-DD)"),
):
    """Get hourly weather data for a station on a specific date (archive)."""
    if station_key not in TRAIN_STATIONS:
        raise HTTPException(404, f"Unknown station: {station_key}")

    from datetime import date as date_type
    try:
        d = date_type.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(400, "Invalid date format, use YYYY-MM-DD")

    s = TRAIN_STATIONS[station_key]
    data = fetch_hourly_weather(s["lat"], s["lng"], d, d)
    if not data:
        raise HTTPException(502, "Failed to fetch hourly data from Open-Meteo")

    return {"station_key": station_key, "date": date_str, "hourly": data["hourly"]}


@router.get("/history/{station_key}")
def get_station_history(
    station_key: str,
    start: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end: date = Query(None, description="End date (YYYY-MM-DD), defaults to today"),
):
    """Get raw hourly weather data for a station over a date range."""
    if station_key not in TRAIN_STATIONS:
        raise HTTPException(404, f"Unknown station: {station_key}")

    end_date = end or date.today()
    if start > end_date:
        raise HTTPException(400, "start date must be before end date")

    data = fetch_hourly_for_station(station_key, start, end_date)
    if not data:
        raise HTTPException(502, "Failed to fetch data from Open-Meteo")

    return {
        "station_key": data["station_key"],
        "station_name": data["station_name"],
        "date_range": {"start": start.isoformat(), "end": end_date.isoformat()},
        "hourly": data["hourly"],
    }


@router.get("/forecast/{station_key}")
def get_station_forecast(
    station_key: str,
    days: int = Query(16, ge=1, le=16, description="Forecast days (1-16)"),
):
    """Get 16-day weather forecast for a train station."""
    if station_key not in TRAIN_STATIONS:
        raise HTTPException(404, f"Unknown station: {station_key}")

    s = TRAIN_STATIONS[station_key]
    data = fetch_forecast(s["lat"], s["lng"], days)
    if not data:
        raise HTTPException(502, "Failed to fetch forecast from Open-Meteo")

    return {
        "station_key": station_key,
        "station_name": s["name"],
        "lat": s["lat"],
        "lng": s["lng"],
        "daily": data["daily"],
    }


@router.get("/forecast-hourly/{station_key}")
def get_station_forecast_hourly(
    station_key: str,
    days: int = Query(16, ge=1, le=16, description="Forecast days (1-16)"),
):
    """Get hourly forecast data for a station."""
    if station_key not in TRAIN_STATIONS:
        raise HTTPException(404, f"Unknown station: {station_key}")

    s = TRAIN_STATIONS[station_key]
    data = fetch_hourly_forecast(s["lat"], s["lng"], days)
    if not data:
        raise HTTPException(502, "Failed to fetch hourly forecast from Open-Meteo")

    return {"station_key": station_key, "hourly": data["hourly"]}
