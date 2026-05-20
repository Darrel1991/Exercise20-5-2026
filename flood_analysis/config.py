"""
Flood analysis configuration.

Malaysian flood-prone locations with coordinates, sourced from historical
flood events (2014-2024 major floods: Kelantan, Pahang, Terengganu, Johor,
Selangor, Sarawak).
"""

# Open-Meteo API base URLs (no API key required)
ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"
FLOOD_API = "https://flood-api.open-meteo.com/v1/flood"

# Daily weather variables to fetch for flood analysis
WEATHER_VARIABLES = [
    "precipitation_sum",        # Total daily precipitation (mm)
    "rain_sum",                 # Total daily rain, excl. snow (mm)
    "precipitation_hours",      # Hours with precipitation
    "temperature_2m_max",
    "temperature_2m_min",
    "et0_fao_evapotranspiration",  # Evapotranspiration — soil saturation indicator
]

# Flood risk thresholds (daily precipitation in mm)
# Calibrated for Open-Meteo gridded reanalysis data, which smooths peaks
# over ~10-25km² cells. Real gauge readings are typically 2-3x higher.
RAIN_THRESHOLD_HEAVY = 25.0        # Heavy rain (gridded equivalent of ~60mm gauge)
RAIN_THRESHOLD_VERY_HEAVY = 40.0   # Very heavy rain (gridded equivalent of ~120mm gauge)
RAIN_THRESHOLD_EXTREME = 60.0      # Extreme — flood trigger (gridded equiv of ~150-200mm gauge)
RAIN_CONSECUTIVE_DAYS = 3          # Sustained rain window for flood risk

# Malaysian flood-prone monitoring locations
# Keyed by a short slug; each entry has name, state, lat, lng, and notes
FLOOD_LOCATIONS = {
    # ── Kelantan (worst-hit state, 2014 & 2021 mega-floods) ──────────
    "kota-bharu": {
        "name": "Kota Bharu",
        "state": "Kelantan",
        "lat": 6.12, "lng": 102.25,
        "river": "Kelantan River",
    },
    "kuala-krai": {
        "name": "Kuala Krai",
        "state": "Kelantan",
        "lat": 5.53, "lng": 102.20,
        "river": "Kelantan River / Lebir River",
    },
    "gua-musang": {
        "name": "Gua Musang",
        "state": "Kelantan",
        "lat": 4.88, "lng": 101.97,
        "river": "Galas River",
    },
    "tanah-merah": {
        "name": "Tanah Merah",
        "state": "Kelantan",
        "lat": 5.81, "lng": 102.15,
        "river": "Kelantan River",
    },

    # ── Terengganu ───────────────────────────────────────────────────
    "kuala-terengganu": {
        "name": "Kuala Terengganu",
        "state": "Terengganu",
        "lat": 5.31, "lng": 103.13,
        "river": "Terengganu River",
    },
    "kemaman": {
        "name": "Kemaman",
        "state": "Terengganu",
        "lat": 4.23, "lng": 103.42,
        "river": "Kemaman River",
    },
    "dungun": {
        "name": "Dungun",
        "state": "Terengganu",
        "lat": 4.76, "lng": 103.42,
        "river": "Dungun River",
    },

    # ── Pahang ───────────────────────────────────────────────────────
    "kuantan": {
        "name": "Kuantan",
        "state": "Pahang",
        "lat": 3.81, "lng": 103.33,
        "river": "Kuantan River",
    },
    "temerloh": {
        "name": "Temerloh",
        "state": "Pahang",
        "lat": 3.45, "lng": 102.42,
        "river": "Pahang River",
    },
    "pekan": {
        "name": "Pekan",
        "state": "Pahang",
        "lat": 3.49, "lng": 103.40,
        "river": "Pahang River",
    },
    "bentong": {
        "name": "Bentong",
        "state": "Pahang",
        "lat": 3.52, "lng": 101.91,
        "river": "Bentong River",
    },

    # ── Johor (2006/2007, 2023 floods) ──────────────────────────────
    "johor-bahru": {
        "name": "Johor Bahru",
        "state": "Johor",
        "lat": 1.48, "lng": 103.76,
        "river": "Segget River",
    },
    "kota-tinggi": {
        "name": "Kota Tinggi",
        "state": "Johor",
        "lat": 1.73, "lng": 103.90,
        "river": "Johor River",
    },
    "segamat": {
        "name": "Segamat",
        "state": "Johor",
        "lat": 2.51, "lng": 102.82,
        "river": "Muar River",
    },
    "mersing": {
        "name": "Mersing",
        "state": "Johor",
        "lat": 2.43, "lng": 103.84,
        "river": "Mersing River",
    },

    # ── Selangor / KL (2021 Shah Alam flood) ────────────────────────
    "shah-alam": {
        "name": "Shah Alam",
        "state": "Selangor",
        "lat": 3.07, "lng": 101.52,
        "river": "Klang River",
    },
    "klang": {
        "name": "Klang",
        "state": "Selangor",
        "lat": 3.04, "lng": 101.45,
        "river": "Klang River",
    },
    "hulu-langat": {
        "name": "Hulu Langat",
        "state": "Selangor",
        "lat": 3.22, "lng": 101.86,
        "river": "Langat River",
    },
    "kuala-lumpur": {
        "name": "Kuala Lumpur",
        "state": "W.P. Kuala Lumpur",
        "lat": 3.14, "lng": 101.69,
        "river": "Klang River / Gombak River",
    },

    # ── Perak ────────────────────────────────────────────────────────
    "kinta": {
        "name": "Kinta (Ipoh)",
        "state": "Perak",
        "lat": 4.60, "lng": 101.07,
        "river": "Kinta River",
    },
    "hilir-perak": {
        "name": "Hilir Perak",
        "state": "Perak",
        "lat": 4.03, "lng": 100.88,
        "river": "Perak River",
    },

    # ── Kedah ────────────────────────────────────────────────────────
    "alor-setar": {
        "name": "Alor Setar",
        "state": "Kedah",
        "lat": 6.12, "lng": 100.37,
        "river": "Kedah River",
    },

    # ── Pulau Pinang ─────────────────────────────────────────────────
    "penang": {
        "name": "Georgetown",
        "state": "Pulau Pinang",
        "lat": 5.41, "lng": 100.34,
        "river": "Pinang River",
    },

    # ── Sarawak (Sibu & Kuching floods) ──────────────────────────────
    "sibu": {
        "name": "Sibu",
        "state": "Sarawak",
        "lat": 2.30, "lng": 111.85,
        "river": "Rajang River",
    },
    "kuching": {
        "name": "Kuching",
        "state": "Sarawak",
        "lat": 1.55, "lng": 110.35,
        "river": "Sarawak River",
    },

    # ── Sabah ────────────────────────────────────────────────────────
    "kota-kinabalu": {
        "name": "Kota Kinabalu",
        "state": "Sabah",
        "lat": 5.98, "lng": 116.07,
        "river": "Moyog River",
    },
    "penampang": {
        "name": "Penampang",
        "state": "Sabah",
        "lat": 5.93, "lng": 116.12,
        "river": "Moyog River",
    },
}
