from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.connection import get_db
from db.repository import get_positions_at_time

router = APIRouter(prefix="/api/history", tags=["history"])


def _position_to_dict(vp) -> dict:
    return {
        "vehicle_id": vp.vehicle_id,
        "agency": vp.agency,
        "trip_id": vp.trip_id,
        "route_id": vp.route_id,
        "latitude": vp.latitude,
        "longitude": vp.longitude,
        "bearing": vp.bearing,
        "speed": vp.speed,
        "timestamp": vp.timestamp.isoformat() if vp.timestamp else None,
    }


@router.get("/snapshot")
def snapshot(
    timestamp: datetime = Query(..., description="ISO8601 timestamp"),
    agency: str = Query("all"),
    db: Session = Depends(get_db),
):
    """All vehicle positions at a given point in time."""
    positions = get_positions_at_time(db, at=timestamp, agency=agency)
    return {"timestamp": timestamp.isoformat(), "count": len(positions), "vehicles": [_position_to_dict(p) for p in positions]}


@router.get("/heatmap")
def heatmap(
    from_dt: datetime = Query(..., alias="from"),
    to_dt: datetime = Query(..., alias="to"),
    agency: str = Query("all"),
    db: Session = Depends(get_db),
):
    """Lat/lng density data for heatmap rendering."""
    # Return raw positions in the time range; client-side does density calc
    positions = get_positions_at_time(db, at=from_dt, agency=agency, window_seconds=int((to_dt - from_dt).total_seconds()))
    points = [{"lat": p.latitude, "lng": p.longitude} for p in positions]
    return {"count": len(points), "points": points}
