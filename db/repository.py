import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text, delete, func as sa_func
from sqlalchemy.orm import Session

from db.models import VehiclePosition, GtfsRoute, GtfsStop, IngestionLog

logger = logging.getLogger(__name__)


# ── Vehicle Positions ────────────────────────────────────────────────

def bulk_insert_positions(db: Session, positions: list[dict]) -> int:
    """Insert a batch of vehicle positions. Returns count inserted."""
    if not positions:
        return 0
    db.bulk_insert_mappings(VehiclePosition, positions)
    db.commit()
    return len(positions)


def get_latest_positions(
    db: Session, agency: Optional[str] = None, seconds: int = 60
) -> list[VehiclePosition]:
    """Get the most recent position per vehicle within the last N seconds."""
    cutoff = datetime.utcnow() - timedelta(seconds=seconds)
    # Subquery: latest timestamp per vehicle
    max_ts = sa_func.max(VehiclePosition.timestamp).label("max_ts")
    latest_sq = (
        db.query(
            VehiclePosition.vehicle_id,
            VehiclePosition.agency,
            max_ts,
        )
        .filter(VehiclePosition.timestamp >= cutoff)
    )
    if agency and agency != "all":
        latest_sq = latest_sq.filter(VehiclePosition.agency == agency)
    latest_sq = latest_sq.group_by(
        VehiclePosition.vehicle_id, VehiclePosition.agency
    ).subquery()

    rows = (
        db.query(VehiclePosition)
        .join(
            latest_sq,
            (VehiclePosition.vehicle_id == latest_sq.c.vehicle_id)
            & (VehiclePosition.agency == latest_sq.c.agency)
            & (VehiclePosition.timestamp == latest_sq.c.max_ts),
        )
        .all()
    )
    return rows


def get_vehicle_history(
    db: Session,
    vehicle_id: str,
    from_dt: Optional[datetime] = None,
    to_dt: Optional[datetime] = None,
) -> list[VehiclePosition]:
    """Get position trail for a specific vehicle."""
    q = db.query(VehiclePosition).filter(VehiclePosition.vehicle_id == vehicle_id)
    if from_dt:
        q = q.filter(VehiclePosition.timestamp >= from_dt)
    if to_dt:
        q = q.filter(VehiclePosition.timestamp <= to_dt)
    return q.order_by(VehiclePosition.timestamp.asc()).all()


def get_positions_at_time(
    db: Session, at: datetime, agency: Optional[str] = None, window_seconds: int = 30
) -> list[VehiclePosition]:
    """Get all vehicle positions near a given timestamp (±window)."""
    lo = at - timedelta(seconds=window_seconds)
    hi = at + timedelta(seconds=window_seconds)
    q = db.query(VehiclePosition).filter(
        VehiclePosition.timestamp.between(lo, hi)
    )
    if agency and agency != "all":
        q = q.filter(VehiclePosition.agency == agency)
    return q.all()


def get_stalled_vehicles(
    db: Session, threshold_minutes: int = 5, agency: Optional[str] = None
) -> list[dict]:
    """Find vehicles whose position hasn't changed for N minutes."""
    cutoff = datetime.utcnow() - timedelta(minutes=threshold_minutes)
    sql = text("""
        WITH recent AS (
            SELECT vehicle_id, agency, latitude, longitude, timestamp,
                   ROW_NUMBER() OVER (
                       PARTITION BY vehicle_id, agency
                       ORDER BY timestamp DESC
                   ) AS rn
            FROM vehicle_positions
            WHERE timestamp >= :cutoff
        ),
        latest AS (SELECT * FROM recent WHERE rn = 1),
        earliest AS (SELECT * FROM recent WHERE rn = (
            SELECT MAX(rn) FROM recent r2
            WHERE r2.vehicle_id = recent.vehicle_id AND r2.agency = recent.agency
        ))
        SELECT l.vehicle_id, l.agency, l.latitude, l.longitude,
               l.timestamp as last_seen,
               e.timestamp as first_seen
        FROM latest l
        JOIN earliest e ON l.vehicle_id = e.vehicle_id AND l.agency = e.agency
        WHERE ABS(l.latitude - e.latitude) < 0.0001
          AND ABS(l.longitude - e.longitude) < 0.0001
          AND DATEDIFF(MINUTE, e.timestamp, l.timestamp) >= :threshold
    """)
    params = {"cutoff": cutoff, "threshold": threshold_minutes}
    if agency and agency != "all":
        # Wrap with agency filter
        sql = text(str(sql) + " AND l.agency = :agency")
        params["agency"] = agency

    rows = db.execute(sql, params).fetchall()
    return [dict(r._mapping) for r in rows]


# ── Agencies & Ingestion Log ─────────────────────────────────────────

def log_ingestion(
    db: Session, agency: str, vehicle_count: Optional[int], status: str,
    error_message: Optional[str] = None
):
    """Write an ingestion log entry."""
    entry = IngestionLog(
        agency=agency,
        vehicle_count=vehicle_count,
        status=status,
        error_message=error_message,
    )
    db.add(entry)
    db.commit()


def get_agency_status(db: Session) -> list[dict]:
    """Get latest ingestion status per agency."""
    sql = text("""
        WITH ranked AS (
            SELECT agency, fetched_at, vehicle_count, status, error_message,
                   ROW_NUMBER() OVER (PARTITION BY agency ORDER BY fetched_at DESC) AS rn
            FROM ingestion_log
        )
        SELECT agency, fetched_at, vehicle_count, status, error_message
        FROM ranked WHERE rn = 1
    """)
    rows = db.execute(sql).fetchall()
    return [dict(r._mapping) for r in rows]


# ── GTFS Static ──────────────────────────────────────────────────────

def upsert_routes(db: Session, agency: str, routes: list[dict]):
    """Replace all routes for an agency with fresh static data."""
    db.query(GtfsRoute).filter(GtfsRoute.agency == agency).delete()
    for r in routes:
        r["agency"] = agency
    if routes:
        db.bulk_insert_mappings(GtfsRoute, routes)
    db.commit()


def upsert_stops(db: Session, agency: str, stops: list[dict]):
    """Replace all stops for an agency with fresh static data."""
    db.query(GtfsStop).filter(GtfsStop.agency == agency).delete()
    for s in stops:
        s["agency"] = agency
    if stops:
        db.bulk_insert_mappings(GtfsStop, stops)
    db.commit()


def get_routes(db: Session, agency: Optional[str] = None) -> list[GtfsRoute]:
    q = db.query(GtfsRoute)
    if agency:
        q = q.filter(GtfsRoute.agency == agency)
    return q.all()


def get_stops(db: Session, agency: Optional[str] = None) -> list[GtfsStop]:
    q = db.query(GtfsStop)
    if agency:
        q = q.filter(GtfsStop.agency == agency)
    return q.all()


# ── Maintenance ──────────────────────────────────────────────────────

def purge_old_positions(db: Session, days: int = 30) -> int:
    """Delete vehicle positions older than N days. Returns count deleted."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    result = db.execute(
        delete(VehiclePosition).where(VehiclePosition.timestamp < cutoff)
    )
    db.commit()
    return result.rowcount
