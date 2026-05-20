import csv
import io
import logging
import zipfile

import requests

from config import GTFS_STATIC_BASE, STATIC_AGENCY_URL_MAP
from db.connection import SessionLocal
from db.repository import upsert_routes, upsert_stops

logger = logging.getLogger(__name__)


def _download_zip(agency_key: str) -> zipfile.ZipFile | None:
    """Download GTFS static ZIP for an agency."""
    url_path = STATIC_AGENCY_URL_MAP.get(agency_key)
    if not url_path:
        logger.warning("No static feed mapping for %s", agency_key)
        return None

    url = f"{GTFS_STATIC_BASE}/{url_path}"
    logger.info("Downloading GTFS static for %s from %s", agency_key, url)

    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return zipfile.ZipFile(io.BytesIO(resp.content))


def _parse_csv(zf: zipfile.ZipFile, filename: str) -> list[dict]:
    """Parse a CSV file inside the ZIP, returning list of dicts."""
    if filename not in zf.namelist():
        return []
    with zf.open(filename) as f:
        reader = csv.DictReader(io.TextIOWrapper(f, encoding="utf-8-sig"))
        return list(reader)


def load_static_for_agency(agency_key: str):
    """Download and parse GTFS static feed, then upsert routes & stops."""
    try:
        zf = _download_zip(agency_key)
        if not zf:
            return

        # Parse routes
        raw_routes = _parse_csv(zf, "routes.txt")
        routes = [
            {
                "route_id": r.get("route_id", ""),
                "route_short_name": r.get("route_short_name"),
                "route_long_name": r.get("route_long_name"),
                "route_type": int(r["route_type"]) if r.get("route_type") else None,
            }
            for r in raw_routes
        ]

        # Parse stops
        raw_stops = _parse_csv(zf, "stops.txt")
        stops = [
            {
                "stop_id": s.get("stop_id", ""),
                "stop_name": s.get("stop_name"),
                "stop_lat": float(s["stop_lat"]) if s.get("stop_lat") else None,
                "stop_lon": float(s["stop_lon"]) if s.get("stop_lon") else None,
            }
            for s in raw_stops
        ]

        db = SessionLocal()
        try:
            upsert_routes(db, agency_key, routes)
            upsert_stops(db, agency_key, stops)
            logger.info(
                "Loaded static data for %s: %d routes, %d stops",
                agency_key, len(routes), len(stops),
            )
        finally:
            db.close()

    except Exception:
        logger.exception("Failed to load static feed for %s", agency_key)


def load_all_static():
    """Load static feeds for all configured agencies."""
    for agency_key in STATIC_AGENCY_URL_MAP:
        load_static_for_agency(agency_key)
