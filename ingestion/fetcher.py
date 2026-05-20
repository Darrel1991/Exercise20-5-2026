import logging
from datetime import datetime, timezone

import requests
from google.transit import gtfs_realtime_pb2

from config import (
    GTFS_RT_BASE,
    AGENCY_URL_MAP,
    MALAYSIA_LAT_MIN,
    MALAYSIA_LAT_MAX,
    MALAYSIA_LNG_MIN,
    MALAYSIA_LNG_MAX,
)

logger = logging.getLogger(__name__)

# Occupancy enum from GTFS spec
OCCUPANCY_MAP = {
    0: "EMPTY",
    1: "MANY_SEATS_AVAILABLE",
    2: "FEW_SEATS_AVAILABLE",
    3: "STANDING_ROOM_ONLY",
    4: "CRUSHED_STANDING_ROOM_ONLY",
    5: "FULL",
    6: "NOT_ACCEPTING_PASSENGERS",
}

VEHICLE_STATUS_MAP = {
    0: "INCOMING_AT",
    1: "STOPPED_AT",
    2: "IN_TRANSIT_TO",
}


def _in_malaysia(lat: float, lng: float) -> bool:
    return MALAYSIA_LAT_MIN <= lat <= MALAYSIA_LAT_MAX and MALAYSIA_LNG_MIN <= lng <= MALAYSIA_LNG_MAX


def _clean_trip_id(agency_key: str, trip_id: str) -> str:
    """Strip service ID prefix for Penang buses."""
    if agency_key == "prasarana-rapid-bus-penang" and trip_id:
        parts = trip_id.split("_", 1)
        if len(parts) == 2:
            return parts[1]
    return trip_id


def fetch_agency(agency_key: str) -> list[dict]:
    """
    Fetch GTFS Realtime vehicle positions for a single agency.
    Returns a list of position dicts ready for DB insertion.
    """
    url_path = AGENCY_URL_MAP.get(agency_key)
    if not url_path:
        logger.error("Unknown agency key: %s", agency_key)
        return []

    url = f"{GTFS_RT_BASE}/{url_path}"
    logger.info("Fetching %s from %s", agency_key, url)

    response = requests.get(url, timeout=15)
    response.raise_for_status()

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(response.content)

    positions = []
    for entity in feed.entity:
        if not entity.HasField("vehicle"):
            continue

        v = entity.vehicle
        if not v.HasField("position"):
            continue

        lat = v.position.latitude
        lng = v.position.longitude

        # E028: drop erroneous GPS outside Malaysia
        if not _in_malaysia(lat, lng):
            logger.debug(
                "Dropping out-of-bounds position for %s: (%.4f, %.4f)",
                agency_key, lat, lng,
            )
            continue

        trip_id = v.trip.trip_id if v.HasField("trip") else None
        route_id = v.trip.route_id if v.HasField("trip") else None
        trip_id = _clean_trip_id(agency_key, trip_id)

        ts = (
            datetime.fromtimestamp(v.timestamp, tz=timezone.utc).replace(tzinfo=None)
            if v.timestamp
            else datetime.utcnow()
        )

        positions.append({
            "agency": agency_key,
            "vehicle_id": v.vehicle.id if v.HasField("vehicle") else entity.id,
            "trip_id": trip_id,
            "route_id": route_id,
            "latitude": lat,
            "longitude": lng,
            "bearing": v.position.bearing if v.position.HasField("bearing") else None,
            "speed": v.position.speed if v.position.HasField("speed") else None,
            "occupancy_status": OCCUPANCY_MAP.get(v.occupancy_status)
                if v.HasField("occupancy_status") else None,
            "current_status": VEHICLE_STATUS_MAP.get(v.current_status)
                if v.HasField("current_status") else None,
            "stop_id": v.stop_id if v.stop_id else None,
            "timestamp": ts,
        })

    logger.info("Parsed %d positions for %s", len(positions), agency_key)
    return positions
