"""
Storm risk analysis using ERA5 HOURLY data with calibrated thresholds.

Thunderstorm detection aligned with Open-Meteo forecast API's thunderstorm
classification (WMO 95/96/99). Thresholds calibrated to ERA5 reanalysis
distribution in Malaysia.

A "storm hour" = any hour meeting at least one criterion.
A "storm day" = any day with at least one storm hour.
Roll up: storm hours → storm days → monthly → yearly → heatmap.

No fake calibration. Direct threshold comparison on hourly data.
"""

import logging
from collections import defaultdict

from thunder_analysis.config import (
    THUNDER_RAIN_ONLY,
    THUNDER_RAIN_COMBO,
    THUNDER_GUST_COMBO,
    THUNDER_GUST_ONLY,
    RAIN_HEAVY,
    RAIN_LIGHT,
    RAIN_DRIZZLE,
    CONSECUTIVE_STORM_DAYS,
    WMO_THUNDER_CODES,
    CAPE_LIGHTNING,
    CAPE_HIGH,
    CAPE_EXTREME,
)

logger = logging.getLogger(__name__)

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


def analyze_thunderstorm_risk(hourly_data: dict) -> dict:
    """Analyze hourly weather data for storm risk.

    Args:
        hourly_data: dict with parallel arrays from Open-Meteo hourly endpoint
                     (time, rain, wind_gusts_10m, weathercode, temperature_2m)

    A thunderstorm hour = meets any ERA5-calibrated criterion (see config).
    A thunderstorm day = any day with at least one thunderstorm hour.
    """
    times = hourly_data.get("time", [])
    rain_arr = hourly_data.get("rain", [])
    gust_arr = hourly_data.get("wind_gusts_10m", [])
    code_arr = hourly_data.get("weathercode", [])
    cape_arr = hourly_data.get("cape", [])

    if not times:
        return {"error": "No data available"}

    total_hours = len(times)

    # ── Pass 1: Classify each hour ─────────────────────────────────
    # Thunderstorm detection (priority order):
    #   1) WMO weather code 95/96/99 (model-detected, highest confidence)
    #   2) Heavy rain burst alone
    #   3) Moderate rain + gusts (convective signature)
    #   4) Severe gust alone (likely downdraft)
    # CAPE tracked for lightning potential indicator.
    days_data = defaultdict(lambda: {
        "storm_hours": 0,
        "wmo_thunder_hours": 0,    # hours with WMO 95/96/99
        "lightning_hours": 0,      # hours with CAPE >= 500 J/kg
        "heavy_rain_hours": 0,
        "light_rain_hours": 0,
        "drizzle_hours": 0,
        "total_rain_mm": 0.0,
        "max_rain_mmh": 0.0,
        "max_gust_kmh": 0.0,
        "max_cape": 0.0,
        "rain_hours": 0,
        "max_category": "clear",
        "storm_hour_details": [],
    })

    total_storm_hours = 0
    total_wmo_thunder_hours = 0

    for i in range(total_hours):
        dt_str = times[i]
        date_key = dt_str[:10]
        hour_str = dt_str[11:16]

        r = rain_arr[i] if i < len(rain_arr) and rain_arr[i] is not None else 0.0
        g = gust_arr[i] if i < len(gust_arr) and gust_arr[i] is not None else 0.0
        wc = code_arr[i] if i < len(code_arr) and code_arr[i] is not None else 0
        cape = cape_arr[i] if i < len(cape_arr) and cape_arr[i] is not None else 0.0

        # Thunderstorm detection (priority order — trigger attribution)
        trigger = None
        if wc in WMO_THUNDER_CODES:
            trigger = f"WMO code {wc} (model-detected thunderstorm)"
        elif r >= THUNDER_RAIN_ONLY:
            trigger = f"Rain {r:.1f}mm/h >= {THUNDER_RAIN_ONLY}mm/h (heavy rain burst)"
        elif r >= THUNDER_RAIN_COMBO and g >= THUNDER_GUST_COMBO:
            trigger = f"Rain {r:.1f}mm/h + Gust {g:.1f}km/h (convective signature)"
        elif g >= THUNDER_GUST_ONLY:
            trigger = f"Gust {g:.1f}km/h >= {THUNDER_GUST_ONLY}km/h (severe downdraft)"

        is_storm_hour = trigger is not None
        is_wmo_thunder = wc in WMO_THUNDER_CODES
        is_lightning = cape >= CAPE_LIGHTNING
        is_heavy = r >= RAIN_HEAVY
        is_light = r >= RAIN_LIGHT
        is_drizzle = r >= RAIN_DRIZZLE

        day = days_data[date_key]
        day["total_rain_mm"] += r
        if r > day["max_rain_mmh"]:
            day["max_rain_mmh"] = r
        if g > day["max_gust_kmh"]:
            day["max_gust_kmh"] = g
        if cape > day["max_cape"]:
            day["max_cape"] = cape
        if r > 0:
            day["rain_hours"] += 1
        if is_wmo_thunder:
            day["wmo_thunder_hours"] += 1
            total_wmo_thunder_hours += 1
        if is_lightning:
            day["lightning_hours"] += 1

        if is_storm_hour:
            day["storm_hours"] += 1
            total_storm_hours += 1
            day["max_category"] = "storm"
            day["storm_hour_details"].append({
                "hour": hour_str,
                "rain_mm": round(r, 1),
                "gust_kmh": round(g, 1),
                "cape": round(cape, 0),
                "trigger": trigger,
            })
        elif is_heavy:
            day["heavy_rain_hours"] += 1
            if day["max_category"] != "storm":
                day["max_category"] = "heavy"
        elif is_light:
            day["light_rain_hours"] += 1
            if day["max_category"] not in ("storm", "heavy"):
                day["max_category"] = "light"
        elif is_drizzle:
            day["drizzle_hours"] += 1
            if day["max_category"] == "clear":
                day["max_category"] = "drizzle"

    # ── Pass 2: Build daily summary ────────────────────────────────
    sorted_dates = sorted(days_data.keys())
    total_days = len(sorted_dates)

    storm_days_count = 0
    storm_events = []       # days that had storm hours, latest first
    is_storm_day_map = {}   # date_key → bool

    for date_key in sorted_dates:
        day = days_data[date_key]
        is_storm = day["storm_hours"] > 0
        is_storm_day_map[date_key] = is_storm

        if is_storm:
            storm_days_count += 1
            storm_events.append({
                "date": date_key,
                "storm_hours": day["storm_hours"],
                "wmo_thunder_hours": day["wmo_thunder_hours"],
                "lightning_hours": day["lightning_hours"],
                "total_rain_mm": round(day["total_rain_mm"], 1),
                "max_rain_mmh": round(day["max_rain_mmh"], 1),
                "max_gust_kmh": round(day["max_gust_kmh"], 1),
                "max_cape": round(day["max_cape"], 0),
                "peak_hours": day["storm_hour_details"][:5],
            })

    # Latest first
    storm_events.reverse()

    # ── Consecutive storm days ─────────────────────────────────────
    consecutive_periods = []
    streak_start = None
    streak_count = 0
    streak_rain = 0.0
    streak_max_gust = 0.0
    streak_max_rain = 0.0
    streak_storm_hours = 0

    for date_key in sorted_dates:
        if is_storm_day_map[date_key]:
            if streak_start is None:
                streak_start = date_key
            streak_count += 1
            day = days_data[date_key]
            streak_rain += day["total_rain_mm"]
            streak_max_gust = max(streak_max_gust, day["max_gust_kmh"])
            streak_max_rain = max(streak_max_rain, day["max_rain_mmh"])
            streak_storm_hours += day["storm_hours"]
        else:
            if streak_count >= CONSECUTIVE_STORM_DAYS:
                consecutive_periods.append({
                    "start": streak_start,
                    "end": sorted_dates[sorted_dates.index(date_key) - 1],
                    "days": streak_count,
                    "total_rain_mm": round(streak_rain, 1),
                    "max_rain_mmh": round(streak_max_rain, 1),
                    "max_gust_kmh": round(streak_max_gust, 1),
                    "total_storm_hours": streak_storm_hours,
                })
            streak_start = None
            streak_count = 0
            streak_rain = 0.0
            streak_max_gust = 0.0
            streak_max_rain = 0.0
            streak_storm_hours = 0

    # Trailing streak
    if streak_count >= CONSECUTIVE_STORM_DAYS:
        consecutive_periods.append({
            "start": streak_start,
            "end": sorted_dates[-1],
            "days": streak_count,
            "total_rain_mm": round(streak_rain, 1),
            "max_rain_mmh": round(streak_max_rain, 1),
            "max_gust_kmh": round(streak_max_gust, 1),
            "total_storm_hours": streak_storm_hours,
        })

    consecutive_periods.sort(key=lambda p: p["days"], reverse=True)

    # ── Monthly breakdown ──────────────────────────────────────────
    monthly = {}
    for date_key in sorted_dates:
        month_key = date_key[:7]  # "YYYY-MM"
        if month_key not in monthly:
            monthly[month_key] = {
                "storm_days": 0, "storm_hours": 0,
                "total_rain_mm": 0.0, "max_rain_mmh": 0.0,
                "max_gust_kmh": 0.0,
            }
        day = days_data[date_key]
        m = monthly[month_key]
        if is_storm_day_map[date_key]:
            m["storm_days"] += 1
        m["storm_hours"] += day["storm_hours"]
        m["total_rain_mm"] += day["total_rain_mm"]
        m["max_rain_mmh"] = max(m["max_rain_mmh"], day["max_rain_mmh"])
        m["max_gust_kmh"] = max(m["max_gust_kmh"], day["max_gust_kmh"])

    for m in monthly.values():
        m["total_rain_mm"] = round(m["total_rain_mm"], 1)
        m["max_rain_mmh"] = round(m["max_rain_mmh"], 1)
        m["max_gust_kmh"] = round(m["max_gust_kmh"], 1)

    # ── Yearly breakdown ───────────────────────────────────────────
    yearly = {}
    for date_key in sorted_dates:
        year = date_key[:4]
        if year not in yearly:
            yearly[year] = {
                "storm_days": 0, "storm_hours": 0,
                "total_rain_mm": 0.0, "max_rain_mmh": 0.0,
                "max_gust_kmh": 0.0,
            }
        day = days_data[date_key]
        y = yearly[year]
        if is_storm_day_map[date_key]:
            y["storm_days"] += 1
        y["storm_hours"] += day["storm_hours"]
        y["total_rain_mm"] += day["total_rain_mm"]
        y["max_rain_mmh"] = max(y["max_rain_mmh"], day["max_rain_mmh"])
        y["max_gust_kmh"] = max(y["max_gust_kmh"], day["max_gust_kmh"])

    for y in yearly.values():
        y["total_rain_mm"] = round(y["total_rain_mm"], 1)
        y["max_rain_mmh"] = round(y["max_rain_mmh"], 1)
        y["max_gust_kmh"] = round(y["max_gust_kmh"], 1)

    # ── Heatmap: 3-tier + lightning days per month × year ──────────
    # Each cell: { storm, heavy, clear, lightning }
    # lightning = days with ANY WMO thunder code hour (95/96/99)
    heatmap = {}
    for date_key in sorted_dates:
        year = date_key[:4]
        month = str(int(date_key[5:7]))
        day = days_data[date_key]
        cat = day["max_category"]
        bucket = cat if cat in ("storm", "heavy") else "clear"
        if year not in heatmap:
            heatmap[year] = {}
        if month not in heatmap[year]:
            heatmap[year][month] = {"storm": 0, "heavy": 0, "clear": 0, "lightning": 0}
        heatmap[year][month][bucket] += 1
        if day["wmo_thunder_hours"] > 0:
            heatmap[year][month]["lightning"] += 1

    # ── Risk score (0-100) ─────────────────────────────────────────
    # Based on actual storm hours using calibrated thresholds.
    years_span = max(len(yearly), 1)
    total_rain = sum(days_data[d]["total_rain_mm"] for d in sorted_dates)

    score = 0

    # 1. Storm hours per year — max 30
    storm_hours_per_year = total_storm_hours / years_span
    score += min(30, storm_hours_per_year * 3)

    # 2. Storm days per year — max 25
    storm_days_per_year = storm_days_count / years_span
    score += min(25, storm_days_per_year * 3)

    # 3. Consecutive storm periods — max 20
    short = [p for p in consecutive_periods if p["days"] == 2]
    long = [p for p in consecutive_periods if p["days"] >= 3]
    score += min(20, len(short) * 2 + len(long) * 5)

    # 4. Peak hourly rain intensity — max 15
    max_rain_overall = max((days_data[d]["max_rain_mmh"] for d in sorted_dates), default=0)
    if max_rain_overall >= 30:
        score += 15
    elif max_rain_overall >= 25:
        score += 10
    elif max_rain_overall >= 20:
        score += 5

    # 5. Max gust — max 10
    max_gust_overall = max((days_data[d]["max_gust_kmh"] for d in sorted_dates), default=0)
    if max_gust_overall >= 50:
        score += 10
    elif max_gust_overall >= 45:
        score += 5

    risk_score = min(100, round(score))
    if risk_score >= 70:
        risk_level = "high"
    elif risk_score >= 40:
        risk_level = "moderate"
    else:
        risk_level = "low"

    # ── Peak storm month ───────────────────────────────────────────
    month_storm_totals = {}
    for date_key in sorted_dates:
        if is_storm_day_map[date_key]:
            m = int(date_key[5:7])
            month_storm_totals[m] = month_storm_totals.get(m, 0) + 1

    peak_month = max(month_storm_totals, key=month_storm_totals.get) if month_storm_totals else None

    return {
        "summary": {
            "total_days_analyzed": total_days,
            "total_hours_analyzed": total_hours,
            "date_range": {"start": sorted_dates[0], "end": sorted_dates[-1]} if sorted_dates else None,
            "total_precipitation_mm": round(total_rain, 1),
            "storm_hours": total_storm_hours,
            "storm_days": storm_days_count,
            "wmo_thunder_hours": total_wmo_thunder_hours,
            "lightning_days": sum(1 for d in sorted_dates if days_data[d]["wmo_thunder_hours"] > 0),
            "max_cape": round(max((days_data[d]["max_cape"] for d in sorted_dates), default=0), 0),
            "max_hourly_rain_mm": round(max_rain_overall, 1),
            "max_hourly_gust_kmh": round(max_gust_overall, 1),
            "peak_storm_month": MONTH_NAMES.get(peak_month, "--"),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "thresholds": {
                "thunder_rain_only_mmh": THUNDER_RAIN_ONLY,
                "thunder_combo_rain_mmh": THUNDER_RAIN_COMBO,
                "thunder_combo_gust_kmh": THUNDER_GUST_COMBO,
                "thunder_gust_only_kmh": THUNDER_GUST_ONLY,
                "source": "ERA5-calibrated thunderstorm detection (aligned with forecast model)",
            },
        },
        "storm_events": storm_events[:30],
        "consecutive_storm_periods": consecutive_periods[:15],
        "monthly_totals": monthly,
        "yearly_totals": yearly,
        "heatmap": heatmap,
    }


def compare_stations(results: list[dict]) -> list[dict]:
    """Compare storm risk across multiple stations."""
    comparison = []
    for r in results:
        analysis = r.get("analysis", {})
        summary = analysis.get("summary", {})
        comparison.append({
            "station_key": r["station_key"],
            "station_name": r["station_name"],
            "risk_score": summary.get("risk_score", 0),
            "risk_level": summary.get("risk_level", "unknown"),
            "storm_days": summary.get("storm_days", 0),
            "storm_hours": summary.get("storm_hours", 0),
            "max_hourly_rain_mm": summary.get("max_hourly_rain_mm", 0),
            "max_hourly_gust_kmh": summary.get("max_hourly_gust_kmh", 0),
            "peak_storm_month": summary.get("peak_storm_month", "--"),
        })

    comparison.sort(key=lambda x: x["risk_score"], reverse=True)
    return comparison
