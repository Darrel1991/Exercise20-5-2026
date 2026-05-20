"""
Fetches weather data from data.gov.my MET Malaysia APIs:
  - 7-day forecast (per district/town/state)
  - Active weather warnings
  - Earthquake alerts
"""

import logging
import re
from datetime import datetime, date

import requests
from dateutil.parser import parse as parse_dt

from config import WEATHER_FORECAST_URL, WEATHER_WARNING_URL, WEATHER_EARTHQUAKE_URL

logger = logging.getLogger(__name__)

# ── District/Town coordinates (MET Malaysia locations lack lat/lng) ──
# Hand-mapped from location_id to approximate centroid coordinates.
# Prefixes: St=State, Ds=District, Tn=Town, Rc=Recreation, Dv=Division
LOCATION_COORDS = {
    # Kedah
    "Ds001": (6.3500, 99.8000),   # Langkawi
    "Ds002": (6.1200, 100.3700),  # Kubang Pasu
    "Ds003": (6.1500, 100.5000),  # Padang Terap
    "Ds004": (5.9500, 100.4700),  # Pokok Sena
    "Ds005": (6.1100, 100.3300),  # Alor Setar (Kota Setar)
    "Ds006": (5.8000, 100.4500),  # Pendang
    "Ds007": (5.8000, 100.6000),  # Sik
    "Ds008": (5.6700, 100.4700),  # Yan
    "Ds009": (5.6300, 100.5500),  # Kuala Muda
    "Ds010": (5.5400, 100.4500),  # Kulim
    "Ds011": (5.4800, 100.3900),  # Bandar Baharu
    "Ds012": (5.4500, 100.5000),  # Baling
    # Pulau Pinang
    "Ds013": (5.4100, 100.3300),  # Seberang Perai Utara
    "Ds014": (5.3600, 100.2500),  # Timur Laut
    "Ds015": (5.3100, 100.2500),  # Barat Daya
    "Ds016": (5.3600, 100.4000),  # Seberang Perai Tengah
    "Ds017": (5.2000, 100.4500),  # Seberang Perai Selatan
    # Perak
    "Ds018": (5.2000, 100.7300),  # Hulu Perak
    "Ds019": (5.0500, 100.7300),  # Kerian
    "Ds020": (5.0000, 100.7500),  # Larut, Matang & Selama
    "Ds021": (4.7700, 100.9500),  # Kuala Kangsar
    "Ds022": (4.5500, 100.6000),  # Manjung
    "Ds023": (4.5300, 101.0700),  # Perak Tengah
    "Ds024": (4.7500, 101.1500),  # Kinta
    "Ds025": (4.5000, 101.1000),  # Kampar
    "Ds026": (4.2500, 100.7000),  # Hilir Perak
    "Ds027": (4.0000, 101.3000),  # Batang Padang
    "Ds028": (3.8000, 101.5000),  # Muallim
    # Kelantan
    "Ds029": (6.1200, 102.2500),  # Kota Bharu
    "Ds030": (6.0500, 102.1500),  # Pasir Mas
    "Ds031": (5.9500, 102.0000),  # Tumpat
    "Ds032": (5.8500, 102.1500),  # Pasir Puteh
    "Ds033": (5.8000, 102.0500),  # Bachok
    "Ds034": (5.7500, 102.2000),  # Machang
    "Ds035": (5.5500, 102.1500),  # Tanah Merah
    "Ds036": (5.3000, 101.8500),  # Jeli
    "Ds037": (5.2000, 101.7500),  # Kuala Krai
    "Ds038": (4.8000, 101.7500),  # Gua Musang
    "Ds039": (5.5000, 102.0000),  # Lojing
    # Terengganu
    "Ds040": (5.3100, 103.1300),  # Kuala Terengganu
    "Ds041": (5.3500, 103.0000),  # Hulu Terengganu
    "Ds042": (5.1000, 103.0500),  # Marang
    "Ds043": (5.1500, 103.4000),  # Setiu
    "Ds044": (4.9500, 103.4200),  # Besut
    "Ds045": (4.7500, 103.2000),  # Dungun
    "Ds046": (4.5500, 103.4300),  # Kemaman
    # Pahang
    "Ds047": (3.8000, 103.3300),  # Kuantan
    "Ds048": (3.5400, 103.4500),  # Pekan
    "Ds049": (3.5000, 102.8500),  # Maran
    "Ds050": (3.8000, 102.5000),  # Temerloh
    "Ds051": (4.1000, 101.9000),  # Jerantut
    "Ds052": (4.4700, 101.3800),  # Cameron Highlands
    "Ds053": (4.0700, 101.5000),  # Lipis
    "Ds054": (3.7000, 102.2000),  # Bera
    "Ds055": (3.4000, 102.4000),  # Rompin
    "Ds056": (3.5200, 101.9000),  # Bentong
    "Ds057": (3.4400, 101.7700),  # Raub
    # Selangor
    "Ds058": (3.6900, 101.5100),  # Gombak
    "Ds059": (3.3200, 101.5100),  # Petaling
    "Ds060": (3.4700, 101.7000),  # Hulu Langat
    "Ds061": (3.5500, 101.5300),  # Hulu Selangor
    "Ds062": (3.3200, 101.4500),  # Klang
    "Ds063": (3.0000, 101.4500),  # Kuala Langat
    "Ds064": (2.8500, 101.5500),  # Sepang
    "Ds065": (3.3800, 101.8000),  # Kuala Selangor
    "Ds066": (3.5200, 101.9500),  # Sabak Bernam
    # KL & Putrajaya
    "Ds067": (3.1390, 101.6869),  # Kuala Lumpur
    "Ds068": (2.9264, 101.6964),  # Putrajaya
    # Negeri Sembilan
    "Ds069": (2.7300, 101.9400),  # Seremban
    "Ds070": (2.8000, 102.2500),  # Jelebu
    "Ds071": (2.5200, 102.0800),  # Port Dickson
    "Ds072": (2.7500, 102.2000),  # Kuala Pilah
    "Ds073": (2.4500, 102.3500),  # Tampin
    "Ds074": (2.6000, 102.4000),  # Rembau
    "Ds075": (2.7000, 102.0500),  # Jempol
    # Melaka
    "Ds076": (2.2000, 102.2500),  # Melaka Tengah
    "Ds077": (2.3500, 102.1000),  # Alor Gajah
    "Ds078": (2.1500, 102.4000),  # Jasin
    # Johor
    "Ds079": (1.4800, 103.7600),  # Johor Bahru
    "Ds080": (1.7500, 103.8000),  # Kota Tinggi
    "Ds081": (2.0000, 103.5500),  # Mersing
    "Ds082": (1.8500, 103.0500),  # Kluang
    "Ds083": (1.7400, 103.3800),  # Kulai
    "Ds084": (2.0200, 102.9700),  # Segamat
    "Ds085": (2.0500, 102.5700),  # Muar
    "Ds086": (1.8500, 102.7500),  # Batu Pahat
    "Ds087": (1.5500, 102.9000),  # Pontian
    "Ds088": (2.1200, 102.5000),  # Tangkak
    # Perlis
    "Ds089": (6.4400, 100.2000),  # Perlis
    # Sabah
    "Ds090": (5.9800, 116.0700),  # Kota Kinabalu
    "Ds091": (6.0300, 116.1800),  # Penampang
    "Ds092": (5.8900, 116.0500),  # Papar
    "Ds093": (6.2500, 116.2500),  # Tuaran
    "Ds094": (6.3500, 116.3000),  # Kota Belud
    "Ds095": (6.7200, 116.7400),  # Kudat
    "Ds096": (5.5000, 115.6000),  # Beaufort
    "Ds097": (5.3000, 115.5000),  # Sipitang
    "Ds098": (5.8200, 118.1200),  # Sandakan
    "Ds099": (5.2000, 118.0000),  # Kinabatangan
    "Ds100": (4.3000, 118.0000),  # Tawau
    "Ds101": (4.5800, 117.8900),  # Lahad Datu
    "Ds102": (4.9500, 118.6500),  # Semporna
    "Ds103": (5.3000, 116.9000),  # Ranau
    "Ds104": (4.6000, 116.5000),  # Keningau
    "Ds105": (4.9000, 115.8000),  # Tenom
    "Ds106": (5.0000, 117.5000),  # Beluran
    "Ds107": (6.5000, 116.8500),  # Pitas
    # Sarawak
    "Ds108": (1.5500, 110.3500),  # Kuching
    "Ds109": (1.6500, 110.0500),  # Lundu
    "Ds110": (1.6300, 110.5500),  # Samarahan
    "Ds111": (1.8500, 110.9500),  # Sri Aman
    "Ds112": (2.3000, 111.8500),  # Sibu
    "Ds113": (2.1200, 111.4500),  # Sarikei
    "Ds114": (2.0000, 111.2000),  # Betong
    "Ds115": (2.5000, 111.8000),  # Mukah
    "Ds116": (2.3000, 112.0500),  # Bintulu
    "Ds117": (4.5500, 114.9500),  # Miri
    "Ds118": (4.0000, 114.8000),  # Limbang
    "Ds119": (3.9500, 115.0500),  # Lawas
    "Ds120": (2.7500, 112.5000),  # Kapit
    # Towns (Tn prefix) — major ones
    "Tn001": (6.3500, 99.8000),   # Langkawi
    "Tn002": (6.1100, 100.3300),  # Alor Setar
    "Tn003": (5.4200, 100.3400),  # Georgetown
    "Tn004": (4.5900, 101.0900),  # Ipoh
    "Tn005": (5.2800, 103.1300),  # Kuala Terengganu
    "Tn006": (6.1200, 102.2500),  # Kota Bharu
    "Tn007": (3.8100, 103.3300),  # Kuantan
    "Tn008": (3.1390, 101.6869),  # Kuala Lumpur
    "Tn009": (2.9264, 101.6964),  # Putrajaya
    "Tn010": (2.7300, 101.9400),  # Seremban
    "Tn011": (2.1900, 102.2500),  # Melaka
    "Tn012": (1.4800, 103.7600),  # Johor Bahru
    "Tn013": (6.4400, 100.2000),  # Kangar
    "Tn014": (5.9800, 116.0700),  # Kota Kinabalu
    "Tn015": (1.5500, 110.3500),  # Kuching
    "Tn016": (5.8200, 118.1200),  # Sandakan
    "Tn017": (2.3000, 111.8500),  # Sibu
    "Tn018": (4.5500, 114.9500),  # Miri
    "Tn019": (4.3000, 118.0000),  # Tawau
    "Tn020": (2.3000, 112.0500),  # Bintulu
    "Tn021": (4.4700, 101.3800),  # Cameron Highlands
    "Tn022": (3.5200, 101.9000),  # Bentong
    "Tn023": (2.0000, 103.5500),  # Mersing
    "Tn024": (3.6900, 101.5100),  # Shah Alam
    "Tn025": (5.6500, 100.4900),  # Sungai Petani
    # States (St prefix)
    "St001": (6.1100, 100.3300),  # Kedah
    "St002": (5.3600, 100.2500),  # Pulau Pinang
    "St003": (4.5900, 101.0900),  # Perak
    "St004": (5.5000, 102.1500),  # Kelantan
    "St005": (5.0000, 103.1300),  # Terengganu
    "St006": (3.8000, 102.5000),  # Pahang
    "St007": (3.3800, 101.5300),  # Selangor
    "St008": (3.1390, 101.6869),  # W.P. Kuala Lumpur
    "St009": (2.7300, 101.9400),  # Negeri Sembilan
    "St010": (2.2000, 102.2500),  # Melaka
    "St011": (1.8500, 103.3000),  # Johor
    "St012": (6.4400, 100.2000),  # Perlis
    "St013": (5.5000, 116.5000),  # Sabah
    "St014": (2.5000, 111.5000),  # Sarawak
    "St015": (2.9264, 101.6964),  # W.P. Putrajaya
    "St016": (5.2800, 115.2400),  # W.P. Labuan
}


def _safe_parse_dt(val) -> datetime | None:
    """Parse a datetime string safely, returning None on failure."""
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return parse_dt(str(val))
    except (ValueError, TypeError):
        return None


def _get_coords(location_id: str) -> tuple[float, float] | None:
    """Get lat/lng for a MET Malaysia location ID."""
    return LOCATION_COORDS.get(location_id)


# ── Warning boundary extraction ──────────────────────────────────────

# Matches patterns like:
#   "Latitude: 0-20 North & Longitude: 95-130 East"
#   "Latitud: 0-20 Utara & Longitud: 95-130 Timur"
_BOUNDARY_RE = re.compile(
    r"Latitud(?:e)?:\s*"
    r"(?P<lat_min>\d+(?:\.\d+)?)\s*-\s*(?P<lat_max>\d+(?:\.\d+)?)\s*"
    r"(?:North|Utara|South|Selatan)"
    r".*?"
    r"Longitud(?:e)?:\s*"
    r"(?P<lng_min>\d+(?:\.\d+)?)\s*-\s*(?P<lng_max>\d+(?:\.\d+)?)\s*"
    r"(?:East|Timur|West|Barat)",
    re.IGNORECASE,
)


def parse_warning_boundary(text: str | None) -> dict | None:
    """Extract lat/lng bounding box from warning text.

    Tries two strategies:
    1. Explicit coordinates (e.g. "Latitude: 0-20 North & Longitude: 95-130 East")
    2. District/state name matching — finds all known location names in the text
       and computes a bounding box around their coordinates.

    Returns dict with lat_min, lat_max, lng_min, lng_max or None.
    """
    if not text:
        return None
    # Decode HTML entities (API returns &amp; for &)
    cleaned = text.replace("&amp;", "&")

    # Strategy 1: Explicit lat/lng coordinates
    m = _BOUNDARY_RE.search(cleaned)
    if m:
        return {
            "lat_min": float(m.group("lat_min")),
            "lat_max": float(m.group("lat_max")),
            "lng_min": float(m.group("lng_min")),
            "lng_max": float(m.group("lng_max")),
        }

    # Strategy 2: Match district/state names to coordinates
    return _boundary_from_location_names(cleaned)


# Reverse lookup: location name -> (lat, lng) built from LOCATION_COORDS
# Maps district/state names (lowercase) to coordinates for text matching
_NAME_TO_COORDS: dict[str, tuple[float, float]] = {}

# District names corresponding to LOCATION_COORDS IDs
_DISTRICT_NAMES = {
    # Kedah
    "Ds001": "Langkawi", "Ds002": "Kubang Pasu", "Ds003": "Padang Terap",
    "Ds004": "Pokok Sena", "Ds005": "Kota Setar", "Ds006": "Pendang",
    "Ds007": "Sik", "Ds008": "Yan", "Ds009": "Kuala Muda",
    "Ds010": "Kulim", "Ds011": "Bandar Baharu", "Ds012": "Baling",
    # Pulau Pinang
    "Ds013": "Seberang Perai Utara", "Ds014": "Timur Laut",
    "Ds015": "Barat Daya", "Ds016": "Seberang Perai Tengah",
    "Ds017": "Seberang Perai Selatan",
    # Perak
    "Ds018": "Hulu Perak", "Ds019": "Kerian",
    "Ds020": "Larut, Matang and Selama", "Ds021": "Kuala Kangsar",
    "Ds022": "Manjung", "Ds023": "Perak Tengah", "Ds024": "Kinta",
    "Ds025": "Kampar", "Ds026": "Hilir Perak", "Ds027": "Batang Padang",
    "Ds028": "Muallim",
    # Kelantan
    "Ds029": "Kota Bharu", "Ds030": "Pasir Mas", "Ds031": "Tumpat",
    "Ds032": "Pasir Puteh", "Ds033": "Bachok", "Ds034": "Machang",
    "Ds035": "Tanah Merah", "Ds036": "Jeli", "Ds037": "Kuala Krai",
    "Ds038": "Gua Musang", "Ds039": "Lojing",
    # Terengganu
    "Ds040": "Kuala Terengganu", "Ds041": "Hulu Terengganu",
    "Ds042": "Marang", "Ds043": "Setiu", "Ds044": "Besut",
    "Ds045": "Dungun", "Ds046": "Kemaman",
    # Pahang
    "Ds047": "Kuantan", "Ds048": "Pekan", "Ds049": "Maran",
    "Ds050": "Temerloh", "Ds051": "Jerantut",
    "Ds052": "Cameron Highlands", "Ds053": "Lipis", "Ds054": "Bera",
    "Ds055": "Rompin", "Ds056": "Bentong", "Ds057": "Raub",
    # Selangor
    "Ds058": "Gombak", "Ds059": "Petaling", "Ds060": "Hulu Langat",
    "Ds061": "Hulu Selangor", "Ds062": "Klang", "Ds063": "Kuala Langat",
    "Ds064": "Sepang", "Ds065": "Kuala Selangor", "Ds066": "Sabak Bernam",
    # KL & Putrajaya
    "Ds067": "Kuala Lumpur", "Ds068": "Putrajaya",
    # Negeri Sembilan
    "Ds069": "Seremban", "Ds070": "Jelebu", "Ds071": "Port Dickson",
    "Ds072": "Kuala Pilah", "Ds073": "Tampin", "Ds074": "Rembau",
    "Ds075": "Jempol",
    # Melaka
    "Ds076": "Melaka Tengah", "Ds077": "Alor Gajah", "Ds078": "Jasin",
    # Johor
    "Ds079": "Johor Bahru", "Ds080": "Kota Tinggi", "Ds081": "Mersing",
    "Ds082": "Kluang", "Ds083": "Kulai", "Ds084": "Segamat",
    "Ds085": "Muar", "Ds086": "Batu Pahat", "Ds087": "Pontian",
    "Ds088": "Tangkak",
    # Perlis
    "Ds089": "Perlis",
    # Sabah
    "Ds090": "Kota Kinabalu", "Ds091": "Penampang", "Ds092": "Papar",
    "Ds093": "Tuaran", "Ds094": "Kota Belud", "Ds095": "Kudat",
    "Ds096": "Beaufort", "Ds097": "Sipitang", "Ds098": "Sandakan",
    "Ds099": "Kinabatangan", "Ds100": "Tawau", "Ds101": "Lahad Datu",
    "Ds102": "Semporna", "Ds103": "Ranau", "Ds104": "Keningau",
    "Ds105": "Tenom", "Ds106": "Beluran", "Ds107": "Pitas",
    # Sarawak
    "Ds108": "Kuching", "Ds109": "Lundu", "Ds110": "Samarahan",
    "Ds111": "Sri Aman", "Ds112": "Sibu", "Ds113": "Sarikei",
    "Ds114": "Betong", "Ds115": "Mukah", "Ds116": "Bintulu",
    "Ds117": "Miri", "Ds118": "Limbang", "Ds119": "Lawas",
    "Ds120": "Kapit",
    # States
    "St001": "Kedah", "St002": "Pulau Pinang", "St003": "Perak",
    "St004": "Kelantan", "St005": "Terengganu", "St006": "Pahang",
    "St007": "Selangor", "St008": "Kuala Lumpur", "St009": "Negeri Sembilan",
    "St010": "Melaka", "St011": "Johor", "St012": "Perlis",
    "St013": "Sabah", "St014": "Sarawak", "St015": "Putrajaya",
    "St016": "Labuan",
}

# Build the reverse lookup once at import time
for _loc_id, _name in _DISTRICT_NAMES.items():
    _coords = LOCATION_COORDS.get(_loc_id)
    if _coords:
        _NAME_TO_COORDS[_name.lower()] = _coords

# Add common aliases
_NAME_TO_COORDS["penang"] = LOCATION_COORDS["St002"]
_NAME_TO_COORDS["kl"] = LOCATION_COORDS["Ds067"]
_NAME_TO_COORDS["bagan datuk"] = LOCATION_COORDS["Ds026"]  # alt name for Hilir Perak area


def _boundary_from_location_names(text: str) -> dict | None:
    """Find known district/state names in text and compute bounding box."""
    text_lower = text.lower()
    matched_coords = []

    # Sort by name length descending to match longer names first
    # (e.g. "Kuala Lumpur" before "Kuala")
    for name, coords in sorted(_NAME_TO_COORDS.items(), key=lambda x: -len(x[0])):
        if name in text_lower:
            matched_coords.append(coords)

    if len(matched_coords) < 1:
        return None

    lats = [c[0] for c in matched_coords]
    lngs = [c[1] for c in matched_coords]

    # Add padding (~20km) around points so single-district warnings show a visible area
    PADDING = 0.2
    return {
        "lat_min": round(min(lats) - PADDING, 4),
        "lat_max": round(max(lats) + PADDING, 4),
        "lng_min": round(min(lngs) - PADDING, 4),
        "lng_max": round(max(lngs) + PADDING, 4),
    }


def fetch_forecasts() -> list[dict]:
    """Fetch 7-day weather forecasts for all districts."""
    logger.info("Fetching weather forecasts")
    all_forecasts = []
    try:
        resp = requests.get(WEATHER_FORECAST_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for entry in data:
            loc = entry.get("location", {})
            loc_id = loc.get("location_id", "")
            coords = _get_coords(loc_id)

            all_forecasts.append({
                "location_id": loc_id,
                "location_name": loc.get("location_name", ""),
                "date": entry.get("date"),
                "morning_forecast": entry.get("morning_forecast"),
                "afternoon_forecast": entry.get("afternoon_forecast"),
                "night_forecast": entry.get("night_forecast"),
                "summary_forecast": entry.get("summary_forecast"),
                "summary_when": entry.get("summary_when"),
                "min_temp": entry.get("min_temp"),
                "max_temp": entry.get("max_temp"),
                "latitude": coords[0] if coords else None,
                "longitude": coords[1] if coords else None,
            })

        logger.info("Fetched %d forecast entries", len(all_forecasts))
    except Exception:
        logger.exception("Failed to fetch weather forecasts")

    return all_forecasts


def fetch_warnings() -> list[dict]:
    """Fetch active weather warnings from MET Malaysia."""
    logger.info("Fetching weather warnings")
    warnings = []
    try:
        resp = requests.get(WEATHER_WARNING_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for entry in data:
            issue = entry.get("warning_issue", {})
            text_en = entry.get("text_en")
            text_bm = entry.get("text_bm")
            # Try English text first, fall back to Malay
            boundary = parse_warning_boundary(text_en) or parse_warning_boundary(text_bm)
            rec = {
                "title_en": issue.get("title_en"),
                "title_bm": issue.get("title_bm"),
                "heading_en": entry.get("heading_en"),
                "heading_bm": entry.get("heading_bm"),
                "text_en": text_en,
                "text_bm": text_bm,
                "instruction_en": entry.get("instruction_en"),
                "instruction_bm": entry.get("instruction_bm"),
                "issued": _safe_parse_dt(issue.get("issued")),
                "valid_from": _safe_parse_dt(entry.get("valid_from")),
                "valid_to": _safe_parse_dt(entry.get("valid_to")),
                "boundary_lat_min": boundary["lat_min"] if boundary else None,
                "boundary_lat_max": boundary["lat_max"] if boundary else None,
                "boundary_lng_min": boundary["lng_min"] if boundary else None,
                "boundary_lng_max": boundary["lng_max"] if boundary else None,
            }
            warnings.append(rec)

        logger.info("Fetched %d weather warnings", len(warnings))
    except Exception:
        logger.exception("Failed to fetch weather warnings")

    return warnings


def fetch_earthquakes() -> list[dict]:
    """Fetch earthquake alerts."""
    logger.info("Fetching earthquake data")
    quakes = []
    try:
        resp = requests.get(WEATHER_EARTHQUAKE_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for entry in data:
            quakes.append({
                "location": entry.get("location"),
                "latitude": entry.get("lat"),
                "longitude": entry.get("lon"),
                "magnitude": entry.get("magnitude"),
                "depth": entry.get("depth"),
                "timestamp": _safe_parse_dt(entry.get("timestamp")),
            })

        logger.info("Fetched %d earthquake entries", len(quakes))
    except Exception:
        logger.exception("Failed to fetch earthquake data")

    return quakes
