from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config import ENABLE_AGENCIES
from db.connection import get_db
from db.repository import get_agency_status

router = APIRouter(prefix="/api/agencies", tags=["agencies"])


@router.get("")
def list_agencies(db: Session = Depends(get_db)):
    """List of agencies with latest ingestion status."""
    statuses = get_agency_status(db)
    status_map = {s["agency"]: s for s in statuses}

    result = []
    for key in ENABLE_AGENCIES:
        s = status_map.get(key, {})
        result.append({
            "agency": key,
            "vehicle_count": s.get("vehicle_count"),
            "last_fetched": s.get("fetched_at").isoformat() if s.get("fetched_at") else None,
            "status": s.get("status", "unknown"),
            "error_message": s.get("error_message"),
        })

    return {"agencies": result}
