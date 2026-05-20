"""
Storm analysis configuration for train stations.

Uses ERA5 HOURLY data from Open-Meteo with calibrated thresholds
aligned with what the Forecast API labels as thunderstorms (WMO 95/96/99).
Historical heatmap classification mirrors forecast for consistency.
"""

# Open-Meteo API base URL (no API key required)
ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"

# Hourly weather variables to fetch
HOURLY_VARIABLES = [
    "rain",                 # Hourly rain (mm) — direct measurement per hour
    "wind_gusts_10m",       # Max wind gust in that hour (km/h)
    "weathercode",          # WMO weather code per hour (95/96/99 = thunderstorm)
    "temperature_2m",       # Temperature (°C)
    "cape",                 # Convective Available Potential Energy (J/kg)
]

# WMO thunderstorm codes (direct model-detected thunderstorms)
WMO_THUNDER_CODES = {95, 96, 99}

# CAPE threshold for atmospheric thunderstorm potential (J/kg)
CAPE_LIGHTNING = 500        # J/kg — thunderstorm-favorable
CAPE_HIGH = 1000            # J/kg — moderate thunderstorm energy
CAPE_EXTREME = 2000         # J/kg — severe thunderstorm energy

# ── ERA5-calibrated thunderstorm thresholds ─────────────────────────
# Applied directly to ERA5 hourly data — no calibration needed.
# ── ERA5-Calibrated Thunderstorm Detection ──────────────────────────
# Thresholds calibrated to ERA5 reanalysis data distribution in Malaysia,
# aligned with what the Open-Meteo Forecast API labels as thunderstorms
# (WMO codes 95/96/99). Historical heatmap classification mirrors forecast
# so both tabs are consistent.

# Thunderstorm detection criteria (any one triggers thunderstorm classification)
THUNDER_RAIN_ONLY = 10.0       # mm/h — heavy rain burst indicates thunderstorm in ERA5
THUNDER_RAIN_COMBO = 5.0       # mm/h — with gusts (convective signature)
THUNDER_GUST_COMBO = 25.0      # km/h — with rain burst (downdraft gusts)
THUNDER_GUST_ONLY = 35.0       # km/h — direct severe gust

# Rain severity tiers (based on peak hourly intensity)
RAIN_HEAVY = 5.0            # mm/h — heavy rain (no storm signature)
RAIN_LIGHT = 2.0            # mm/h — light rain
RAIN_DRIZZLE = 0.3          # mm/h — drizzle

# Keep old names for backward compat
RAIN_THRESHOLD = THUNDER_RAIN_ONLY
GUST_THRESHOLD = THUNDER_GUST_ONLY

# Consecutive storm days
CONSECUTIVE_STORM_DAYS = 2

# ── Train Lines & Stations ────────────────────────────────────────────

TRAIN_LINES = {
    "LRT3": {
        "name": "LRT3 Line",
        "color": "#22c55e",  # green
        "stations": [
            "bandar-utama", "kayu-ara", "bu-11", "damansara-idaman",
            "ss-7", "glenmarie-2", "kerjaya", "stadium-shah-alam",
            "dato-menteri", "uitm-shah-alam", "seksyen-7-shah-alam",
            "bandar-baru-klang", "pasar-besar-klang", "jalan-meru",
            "klang", "taman-selatan", "sri-andalas", "klang-jaya",
            "bandar-bukit-tinggi", "johan-setia",
        ],
    },
    "KJ": {
        "name": "KJ Line (Kelana Jaya)",
        "color": "#ef4444",  # red
        "stations": [
            "gombak", "taman-melati", "wangsa-maju", "sri-rampai",
            "setiawangsa", "jelatek", "dato-keramat", "damai",
            "pasar-seni", "kl-sentral", "bank-rakyat-bangsar",
            "abdullah-hukum", "kerinchi", "kl-gateway-universiti",
            "taman-jaya", "asia-jaya", "taman-paramount",
            "taman-bahagia", "kelana-jaya",
        ],
    },
}

# All stations keyed by slug
TRAIN_STATIONS = {
    # ── LRT3 Line ────────────────────────────────────────────────────
    "bandar-utama": {"name": "Bandar Utama", "lat": 3.144864809, "lng": 101.6187367, "line": "LRT3"},
    "kayu-ara": {"name": "Kayu Ara", "lat": 3.134926033, "lng": 101.616721, "line": "LRT3"},
    "bu-11": {"name": "BU 11", "lat": 3.133549326, "lng": 101.604751, "line": "LRT3"},
    "damansara-idaman": {"name": "Damansara Idaman", "lat": 3.122830914, "lng": 101.5942203, "line": "LRT3"},
    "ss-7": {"name": "SS 7", "lat": 3.10630141, "lng": 101.5911281, "line": "LRT3"},
    "glenmarie-2": {"name": "Glenmarie 2", "lat": 3.095346976, "lng": 101.5886934, "line": "LRT3"},
    "kerjaya": {"name": "Kerjaya", "lat": 3.082389102, "lng": 101.5619675, "line": "LRT3"},
    "stadium-shah-alam": {"name": "Stadium Shah Alam", "lat": 3.079989521, "lng": 101.5491153, "line": "LRT3"},
    "dato-menteri": {"name": "Dato Menteri", "lat": 3.069938008, "lng": 101.5211028, "line": "LRT3"},
    "uitm-shah-alam": {"name": "UITM Shah Alam", "lat": 3.0630352, "lng": 101.5011799, "line": "LRT3"},
    "seksyen-7-shah-alam": {"name": "Seksyen 7 Shah Alam", "lat": 3.067562022, "lng": 101.4868013, "line": "LRT3"},
    "bandar-baru-klang": {"name": "Bandar Baru Klang", "lat": 3.062703543, "lng": 101.4657694, "line": "LRT3"},
    "pasar-besar-klang": {"name": "Pasar Besar Klang", "lat": 3.068365265, "lng": 101.4506957, "line": "LRT3"},
    "jalan-meru": {"name": "Jalan Meru", "lat": 3.059081967, "lng": 101.4519616, "line": "LRT3"},
    "klang": {"name": "Klang", "lat": 3.047285518, "lng": 101.4474364, "line": "LRT3"},
    "taman-selatan": {"name": "Taman Selatan", "lat": 3.026925449, "lng": 101.4423874, "line": "LRT3"},
    "sri-andalas": {"name": "Sri Andalas", "lat": 3.0156538, "lng": 101.4403298, "line": "LRT3"},
    "klang-jaya": {"name": "Klang Jaya", "lat": 3.005494943, "lng": 101.4418146, "line": "LRT3"},
    "bandar-bukit-tinggi": {"name": "Bandar Bukit Tinggi", "lat": 2.993292684, "lng": 101.4464987, "line": "LRT3"},
    "johan-setia": {"name": "Johan Setia", "lat": 2.976302412, "lng": 101.4594896, "line": "LRT3"},
    # ── KJ Line (Kelana Jaya) ────────────────────────────────────────
    "gombak": {"name": "Gombak", "lat": 3.231466, "lng": 101.724345, "line": "KJ"},
    "taman-melati": {"name": "Taman Melati", "lat": 3.219542669, "lng": 101.7218239, "line": "KJ"},
    "wangsa-maju": {"name": "Wangsa Maju", "lat": 3.205634, "lng": 101.731913, "line": "KJ"},
    "sri-rampai": {"name": "Sri Rampai", "lat": 3.199208, "lng": 101.737467, "line": "KJ"},
    "setiawangsa": {"name": "Setiawangsa", "lat": 3.176006381, "lng": 101.73584, "line": "KJ"},
    "jelatek": {"name": "Jelatek", "lat": 3.167452481, "lng": 101.7353607, "line": "KJ"},
    "dato-keramat": {"name": "Dato' Keramat", "lat": 3.165306961, "lng": 101.7315841, "line": "KJ"},
    "damai": {"name": "Damai", "lat": 3.164475228, "lng": 101.7244916, "line": "KJ"},
    "pasar-seni": {"name": "Pasar Seni", "lat": 3.142503675, "lng": 101.6952713, "line": "KJ"},
    "kl-sentral": {"name": "KL Sentral", "lat": 3.134250794, "lng": 101.6861222, "line": "KJ"},
    "bank-rakyat-bangsar": {"name": "Bank Rakyat - Bangsar", "lat": 3.127697242, "lng": 101.6791465, "line": "KJ"},
    "abdullah-hukum": {"name": "Abdullah Hukum", "lat": 3.118862802, "lng": 101.6729454, "line": "KJ"},
    "kerinchi": {"name": "Kerinchi", "lat": 3.115555121, "lng": 101.6685572, "line": "KJ"},
    "kl-gateway-universiti": {"name": "KL Gateway - Universiti", "lat": 3.114575509, "lng": 101.6616256, "line": "KJ"},
    "taman-jaya": {"name": "Taman Jaya", "lat": 3.104075113, "lng": 101.6452663, "line": "KJ"},
    "asia-jaya": {"name": "Asia Jaya", "lat": 3.104400298, "lng": 101.6376968, "line": "KJ"},
    "taman-paramount": {"name": "Taman Paramount", "lat": 3.104698047, "lng": 101.6231668, "line": "KJ"},
    "taman-bahagia": {"name": "Taman Bahagia", "lat": 3.110756048, "lng": 101.6126941, "line": "KJ"},
    "kelana-jaya": {"name": "Kelana Jaya", "lat": 3.112449154, "lng": 101.6045305, "line": "KJ"},
}
