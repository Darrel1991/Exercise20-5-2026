from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.connection import get_db
from db.repository import get_latest_positions, get_stalled_vehicles, get_agency_status

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/stalled")
def stalled_vehicles(
    agency: str = Query("all"),
    threshold_minutes: int = Query(5, ge=1),
    db: Session = Depends(get_db),
):
    """Vehicles with no position change for N minutes."""
    stalled = get_stalled_vehicles(db, threshold_minutes=threshold_minutes, agency=agency)
    return {"count": len(stalled), "threshold_minutes": threshold_minutes, "vehicles": stalled}


@router.get("/coverage")
def coverage(
    agency: str = Query("all"),
    db: Session = Depends(get_db),
):
    """Active vehicle count per agency with gap detection."""
    positions = get_latest_positions(db, agency=agency, seconds=120)
    agency_counts: dict[str, int] = {}
    for p in positions:
        agency_counts[p.agency] = agency_counts.get(p.agency, 0) + 1

    return {"agencies": [{"agency": k, "active_vehicles": v} for k, v in agency_counts.items()]}


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    """Dashboard KPIs — total active, stalled, agencies reporting, last update."""
    positions = get_latest_positions(db, seconds=120)
    stalled = get_stalled_vehicles(db, threshold_minutes=5)
    statuses = get_agency_status(db)

    agencies_reporting = sum(1 for s in statuses if s.get("status") == "ok")
    last_update = max(
        (s["fetched_at"] for s in statuses if s.get("fetched_at")),
        default=None,
    )

    return {
        "total_active_vehicles": len(positions),
        "stalled_vehicles": len(stalled),
        "agencies_reporting": agencies_reporting,
        "total_agencies": len(statuses),
        "last_update": last_update.isoformat() if last_update else None,
        "generated_at": datetime.utcnow().isoformat(),
    }
