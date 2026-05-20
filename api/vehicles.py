from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.connection import get_db
from db.repository import get_latest_positions, get_vehicle_history

router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])


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
        "occupancy_status": vp.occupancy_status,
        "current_status": vp.current_status,
        "stop_id": vp.stop_id,
        "timestamp": vp.timestamp.isoformat() if vp.timestamp else None,
    }


@router.get("")
def list_vehicles(
    agency: str = Query("all", description="Agency key or 'all'"),
    db: Session = Depends(get_db),
):
    """Latest position of all active vehicles (last 60 seconds)."""
    positions = get_latest_positions(db, agency=agency)
    return {"count": len(positions), "vehicles": [_position_to_dict(p) for p in positions]}


@router.get("/{vehicle_id}/history")
def vehicle_history(
    vehicle_id: str,
    from_dt: Optional[datetime] = Query(None, alias="from"),
    to_dt: Optional[datetime] = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    """Position trail for a specific vehicle."""
    positions = get_vehicle_history(db, vehicle_id, from_dt, to_dt)
    return {"vehicle_id": vehicle_id, "count": len(positions), "trail": [_position_to_dict(p) for p in positions]}
