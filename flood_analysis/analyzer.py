"""
Flood risk analysis based on historical precipitation data.

Identifies:
- Heavy/extreme rainfall events
- Consecutive rainy days (sustained saturation)
- Monthly/yearly precipitation patterns
- Flood risk periods
- Comparison across locations
"""

import logging
from datetime import date

from flood_analysis.config import (
    RAIN_THRESHOLD_HEAVY,
    RAIN_THRESHOLD_VERY_HEAVY,
    RAIN_THRESHOLD_EXTREME,
    RAIN_CONSECUTIVE_DAYS,
)

logger = logging.getLogger(__name__)


def analyze_flood_risk(daily_data: dict) -> dict:
    """Analyze historical daily weather data for flood risk indicators.

    Args:
        daily_data: dict with parallel arrays from Open-Meteo
                    (time, precipitation_sum, rain_sum, etc.)

    Returns dict with:
        - extreme_events: list of dates with extreme rainfall
        - heavy_rain_days: count of heavy rain days
        - consecutive_rain_periods: sustained rain windows
        - monthly_totals: precipitation by month
        - yearly_totals: precipitation by year
        - risk_score: overall flood risk rating (0-100)
    """
    times = daily_data.get("time", [])
    precip = daily_data.get("precipitation_sum", [])
    rain = daily_data.get("rain_sum", [])

    if not times or not precip:
        return {"error": "No data available"}

    # Use rain_sum if available, otherwise precipitation_sum
    rainfall = rain if rain and any(r is not None for r in rain) else precip

    total_days = len(times)

    # ── Extreme / heavy rain events ─────────────────────────────────
    extreme_events = []
    heavy_days = 0
    very_heavy_days = 0
    extreme_days = 0

    for i, (dt, mm) in enumerate(zip(times, rainfall)):
        if mm is None:
            continue
        if mm >= RAIN_THRESHOLD_EXTREME:
            extreme_events.append({"date": dt, "precipitation_mm": mm, "severity": "extreme"})
            extreme_days += 1
        elif mm >= RAIN_THRESHOLD_VERY_HEAVY:
            extreme_events.append({"date": dt, "precipitation_mm": mm, "severity": "very_heavy"})
            very_heavy_days += 1
        elif mm >= RAIN_THRESHOLD_HEAVY:
            heavy_days += 1

    # Sort by precipitation descending
    extreme_events.sort(key=lambda e: e["precipitation_mm"], reverse=True)

    # ── Consecutive rainy days ──────────────────────────────────────
    consecutive_periods = []
    streak_start = None
    streak_total = 0.0
    streak_days = 0

    for i, (dt, mm) in enumerate(zip(times, rainfall)):
        if mm is not None and mm > 1.0:  # >1mm counts as a rainy day
            if streak_start is None:
                streak_start = dt
            streak_days += 1
            streak_total += mm
        else:
            if streak_days >= RAIN_CONSECUTIVE_DAYS:
                consecutive_periods.append({
                    "start": streak_start,
                    "end": times[i - 1],
                    "days": streak_days,
                    "total_mm": round(streak_total, 1),
                    "avg_mm_per_day": round(streak_total / streak_days, 1),
                })
            streak_start = None
            streak_days = 0
            streak_total = 0.0

    # Handle trailing streak
    if streak_days >= RAIN_CONSECUTIVE_DAYS:
        consecutive_periods.append({
            "start": streak_start,
            "end": times[-1],
            "days": streak_days,
            "total_mm": round(streak_total, 1),
            "avg_mm_per_day": round(streak_total / streak_days, 1),
        })

    # Sort by total precipitation
    consecutive_periods.sort(key=lambda p: p["total_mm"], reverse=True)

    # ── Monthly totals ──────────────────────────────────────────────
    monthly = {}
    for dt, mm in zip(times, rainfall):
        if mm is None:
            continue
        month_key = dt[:7]  # "YYYY-MM"
        if month_key not in monthly:
            monthly[month_key] = {"total_mm": 0.0, "rain_days": 0, "max_daily_mm": 0.0}
        monthly[month_key]["total_mm"] += mm
        if mm > 1.0:
            monthly[month_key]["rain_days"] += 1
        if mm > monthly[month_key]["max_daily_mm"]:
            monthly[month_key]["max_daily_mm"] = mm

    # Round values
    for m in monthly.values():
        m["total_mm"] = round(m["total_mm"], 1)
        m["max_daily_mm"] = round(m["max_daily_mm"], 1)

    # ── Yearly totals ───────────────────────────────────────────────
    yearly = {}
    for dt, mm in zip(times, rainfall):
        if mm is None:
            continue
        year = dt[:4]
        if year not in yearly:
            yearly[year] = {"total_mm": 0.0, "rain_days": 0, "heavy_days": 0, "max_daily_mm": 0.0}
        yearly[year]["total_mm"] += mm
        if mm > 1.0:
            yearly[year]["rain_days"] += 1
        if mm >= RAIN_THRESHOLD_HEAVY:
            yearly[year]["heavy_days"] += 1
        if mm > yearly[year]["max_daily_mm"]:
            yearly[year]["max_daily_mm"] = mm

    for y in yearly.values():
        y["total_mm"] = round(y["total_mm"], 1)
        y["max_daily_mm"] = round(y["max_daily_mm"], 1)

    # ── Monsoon season analysis (Nov-Mar = NE monsoon, peak flood risk) ──
    monsoon_months = {"11", "12", "01", "02", "03"}
    monsoon_rain = 0.0
    non_monsoon_rain = 0.0
    for dt, mm in zip(times, rainfall):
        if mm is None:
            continue
        month = dt[5:7]
        if month in monsoon_months:
            monsoon_rain += mm
        else:
            non_monsoon_rain += mm

    # ── Risk score (0-100) ──────────────────────────────────────────
    # Calibrated for Open-Meteo gridded reanalysis data.
    # Gridded data underestimates peaks by 2-3x vs rain gauges,
    # so thresholds and weights are tuned accordingly.
    total_rain = sum(mm for mm in rainfall if mm is not None)
    avg_daily = total_rain / total_days if total_days > 0 else 0
    years_span = max(len(yearly), 1)
    rainy_days = sum(1 for mm in rainfall if mm is not None and mm > 1.0)

    score = 0

    # 1. Extreme events (>=60mm gridded ≈ 150-200mm gauge) — max 20
    score += min(20, extreme_days * 5)

    # 2. Very heavy rain days (>=40mm gridded) — max 15
    score += min(15, very_heavy_days * 2)

    # 3. Heavy rain frequency per year (>=25mm gridded) — max 15
    heavy_per_year = heavy_days / years_span
    score += min(15, heavy_per_year * 0.5)

    # 4. Consecutive rain periods — max 15
    #    3-4 day streaks get partial credit, 5+ day streaks score more
    short_periods = [p for p in consecutive_periods if 3 <= p["days"] < 5]
    long_periods = [p for p in consecutive_periods if p["days"] >= 5]
    score += min(15, len(short_periods) * 1.5 + len(long_periods) * 4)

    # 5. Annual rainfall volume — max 15
    #    Malaysia avg ~2500mm/yr; flood-prone areas get 3000-4000+
    avg_annual_mm = (total_rain / years_span) if years_span > 0 else 0
    if avg_annual_mm >= 4000:
        score += 15
    elif avg_annual_mm >= 3000:
        score += 10
    elif avg_annual_mm >= 2500:
        score += 6
    elif avg_annual_mm >= 2000:
        score += 3

    # 6. Monsoon concentration — max 10
    #    Graduated: >50% in NE monsoon gets partial credit
    if total_rain > 0:
        monsoon_pct = monsoon_rain / total_rain
        if monsoon_pct > 0.7:
            score += 10
        elif monsoon_pct > 0.6:
            score += 7
        elif monsoon_pct > 0.5:
            score += 4

    # 7. Rainfall intensity & wet day ratio — max 10
    #    High avg daily + high proportion of rainy days = saturated ground
    score += min(5, avg_daily * 0.5)
    wet_ratio = rainy_days / total_days if total_days > 0 else 0
    score += min(5, wet_ratio * 10)  # 50%+ wet days = max 5pts

    risk_score = min(100, round(score))

    if risk_score >= 70:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "moderate"
    else:
        risk_level = "low"

    return {
        "summary": {
            "total_days_analyzed": total_days,
            "date_range": {"start": times[0], "end": times[-1]} if times else None,
            "total_precipitation_mm": round(total_rain, 1),
            "avg_daily_mm": round(avg_daily, 1),
            "risk_score": risk_score,
            "risk_level": risk_level,
        },
        "rain_day_counts": {
            "heavy_25mm": heavy_days,
            "very_heavy_40mm": very_heavy_days,
            "extreme_60mm": extreme_days,
        },
        "extreme_events": extreme_events[:20],  # Top 20
        "consecutive_rain_periods": consecutive_periods[:15],  # Top 15
        "monthly_totals": monthly,
        "yearly_totals": yearly,
        "monsoon_analysis": {
            "ne_monsoon_mm": round(monsoon_rain, 1),
            "non_monsoon_mm": round(non_monsoon_rain, 1),
            "monsoon_pct": round((monsoon_rain / total_rain * 100) if total_rain > 0 else 0, 1),
        },
    }


def compare_locations(results: list[dict]) -> list[dict]:
    """Compare flood risk across multiple locations.

    Args:
        results: list of dicts, each with 'location_key', 'location_name',
                 'state', and 'analysis' (output of analyze_flood_risk).

    Returns sorted list (highest risk first) with comparison data.
    """
    comparison = []
    for r in results:
        analysis = r.get("analysis", {})
        summary = analysis.get("summary", {})
        comparison.append({
            "location_key": r["location_key"],
            "location_name": r["location_name"],
            "state": r["state"],
            "risk_score": summary.get("risk_score", 0),
            "risk_level": summary.get("risk_level", "unknown"),
            "total_precipitation_mm": summary.get("total_precipitation_mm", 0),
            "avg_daily_mm": summary.get("avg_daily_mm", 0),
            "extreme_events": analysis.get("rain_day_counts", {}).get("extreme_200mm", 0),
            "heavy_days": analysis.get("rain_day_counts", {}).get("heavy_60mm", 0),
        })

    comparison.sort(key=lambda x: x["risk_score"], reverse=True)
    return comparison
