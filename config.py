import os
from dotenv import load_dotenv

load_dotenv()

# Database
DB_SERVER = os.getenv("DB_SERVER", r"localhost\SQLEXPRESS")
DB_NAME = os.getenv("DB_NAME", "gtfs_dashboard")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin123")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

# Use Windows Authentication (Trusted_Connection) by default.
# Set DB_USER + DB_PASSWORD in .env to switch to SQL Server Authentication.
if DB_USER and DB_PASSWORD:
    _conn_str = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD}"
    )
else:
    _conn_str = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"Trusted_Connection=yes"
    )

from urllib.parse import quote_plus
DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={quote_plus(_conn_str)}"

# Ingestion
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))
STATIC_REFRESH_HOUR = int(os.getenv("STATIC_REFRESH_HOUR", "4"))

# Enabled agencies (comma-separated keys)
ENABLE_AGENCIES = [
    a.strip() for a in os.getenv(
        "ENABLE_AGENCIES",
        "ktmb,prasarana-rapid-bus-kl,prasarana-rapid-bus-mrtfeeder,mybas-johor"
    ).split(",")
]

# GTFS API base URLs
GTFS_RT_BASE = "https://api.data.gov.my/gtfs-realtime/vehicle-position"
GTFS_STATIC_BASE = "https://api.data.gov.my/gtfs-static"

# Agency key -> API URL path mapping
AGENCY_URL_MAP = {
    "ktmb": "ktmb",
    "prasarana-rapid-bus-kl": "prasarana?category=rapid-bus-kl",
    "prasarana-rapid-bus-mrtfeeder": "prasarana?category=rapid-bus-mrtfeeder",
    "prasarana-rapid-bus-kuantan": "prasarana?category=rapid-bus-kuantan",
    "prasarana-rapid-bus-penang": "prasarana?category=rapid-bus-penang",
    "mybas-kangar": "mybas-kangar",
    "mybas-alor-setar": "mybas-alor-setar",
    "mybas-kota-bharu": "mybas-kota-bharu",
    "mybas-kuala-terengganu": "mybas-kuala-terengganu",
    "mybas-ipoh": "mybas-ipoh",
    "mybas-seremban-a": "mybas-seremban-a",
    "mybas-seremban-b": "mybas-seremban-b",
    "mybas-melaka": "mybas-melaka",
    "mybas-johor": "mybas-johor",
    "mybas-kuching": "mybas-kuching",
}

# Static feed agency keys (same keys, different base URL)
STATIC_AGENCY_URL_MAP = {
    "ktmb": "ktmb",
    "prasarana-rapid-bus-kl": "prasarana?category=rapid-bus-kl",
    "prasarana-rapid-bus-mrtfeeder": "prasarana?category=rapid-bus-mrtfeeder",
    "prasarana-rapid-bus-kuantan": "prasarana?category=rapid-bus-kuantan",
    "prasarana-rapid-bus-penang": "prasarana?category=rapid-bus-penang",
    "prasarana-rapid-rail-kl": "prasarana?category=rapid-rail-kl",
    "mybas-johor": "mybas-johor",
}

# ── Weather API (data.gov.my / MET Malaysia) ────────────────────────
WEATHER_FORECAST_URL = "https://api.data.gov.my/weather/forecast"
WEATHER_WARNING_URL = "https://api.data.gov.my/weather/warning"
WEATHER_EARTHQUAKE_URL = "https://api.data.gov.my/weather/warning/earthquake"
WEATHER_POLL_MINUTES = int(os.getenv("WEATHER_POLL_MINUTES", "30"))

# Malaysia bounding box for GPS validation
MALAYSIA_LAT_MIN = 0.8
MALAYSIA_LAT_MAX = 7.5
MALAYSIA_LNG_MIN = 99.5
MALAYSIA_LNG_MAX = 119.5
