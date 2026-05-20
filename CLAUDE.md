# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Summary

Malaysia public transport disaster analysis dashboard. Ingests GTFS Realtime vehicle position data from data.gov.my, stores snapshots in SQL Server, exposes a FastAPI backend, and renders an interactive Leaflet.js map dashboard.

## Tech Stack

- **Backend:** FastAPI (Python), SQLAlchemy + pyodbc (SQL Server)
- **Ingestion:** APScheduler polling GTFS Realtime protobuf feeds every 30s
- **Frontend:** Single-page HTML with Leaflet.js (map) + Chart.js (stats), Tailwind CSS via CDN
- **Deployment:** Windows Server

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app (starts FastAPI + ingestion scheduler)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Data Sources

- **GTFS Realtime (vehicle positions):** `https://api.data.gov.my/gtfs-realtime/vehicle-position/<agency>` — protobuf format, 30s update cycle
- **GTFS Static (routes/stops/trips):** `https://api.data.gov.my/gtfs-static/<agency>` — ZIP of CSVs, refresh daily at 4 AM
- Supported agencies: ktmb, prasarana (rapid-bus-kl, rapid-bus-mrtfeeder, rapid-bus-kuantan, rapid-bus-penang), mybas-* (kangar, alor-setar, kota-bharu, kuala-terengganu, ipoh, seremban-a, seremban-b, melaka, johor, kuching)

## Architecture

```
main.py                  → FastAPI app entry point
config.py                → DB connection strings, API URLs, settings
ingestion/scheduler.py   → APScheduler polling all feeds
ingestion/fetcher.py     → HTTP fetch + protobuf parse per agency
ingestion/static_loader.py → GTFS Static ZIP download + parse (daily)
db/models.py             → SQLAlchemy table definitions
db/connection.py         → Engine/session setup (pyodbc to SQL Server)
db/repository.py         → DB read/write functions
api/vehicles.py          → /api/vehicles endpoints
api/history.py           → /api/history endpoints (snapshots, heatmaps)
api/agencies.py          → /api/agencies endpoint
api/analysis.py          → /api/analysis endpoints (stalled, coverage, summary)
analysis/anomaly.py      → Stalled vehicle detection, coverage gap analysis
analysis/disaster.py     → Disaster zone overlay logic (Phase 3)
frontend/index.html      → Single-page dashboard
frontend/map.js          → Leaflet map + vehicle markers
frontend/charts.js       → Chart.js stats panels
```

## Key Database Tables

- `vehicle_positions` — every ingested snapshot (high-volume, indexed on agency+timestamp and vehicle_id+timestamp). Purge rows older than 30 days.
- `gtfs_routes` / `gtfs_stops` — static feed enrichment data (composite PK: agency + route_id/stop_id)
- `ingestion_log` — per-agency fetch status tracking (ok/error/empty)

## Data Quality Rules

- **GPS bounding box filter:** Drop positions outside Malaysia (lat 0.8–7.5, lng 99.5–119.5) — handles E028 erroneous GPS
- **rapid-bus-kuantan / rapid-bus-penang:** E003/E004 errors expected — trip_id/route_id may not match static feed. Log warnings, don't crash.
- **rapid-bus-penang:** Strip service ID prefix from trip_id before matching to static feed
- **rapid-rail-kl:** No stable realtime feed — skip realtime, only load static data
- Protobuf fields are optional: always use `HasField()` before accessing nested fields
- Store `ingested_at` (server time) separately from `timestamp` (GPS/feed time)

## Environment Variables (.env)

```
DB_SERVER, DB_NAME, DB_USER, DB_PASSWORD, DB_DRIVER (ODBC Driver 17 for SQL Server)
POLL_INTERVAL_SECONDS (default 30)
STATIC_REFRESH_HOUR (default 4)
ENABLE_AGENCIES (comma-separated agency keys to poll)
```

## Implementation Phases

1. **Phase 1 — Foundation:** Schema, protobuf ingestion, scheduler, /api/vehicles + /api/agencies, basic Leaflet map, ingestion logging
2. **Phase 2 — Analysis:** Stalled detection, coverage gaps, historical queries, Chart.js stats, static feed enrichment
3. **Phase 3 — Disaster Overlay:** Draw-zone queries, timeline replay, flood zone GeoJSON, mass-stoppage alerts, CSV export
4. **Phase 4 — 2026 API Features:** Service alerts + trip update delays (not yet available upstream — stubs only)

## Gotchas

- Do not poll feeds faster than every 30 seconds
- Batch inserts per poll cycle for performance under high write volume
- SQL Server on Windows requires ODBC Driver 17 to be installed on the host
- Future API features (service alerts, trip updates) are not yet available — only prepare schema stubs
