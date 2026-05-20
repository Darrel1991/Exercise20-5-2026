"""
Anomaly detection utilities for vehicle position data.
Used by api/analysis.py — the core queries live in db/repository.py.
This module provides higher-level analysis functions.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from db.repository import get_latest_positions

logger = logging.getLogger(__name__)


def detect_coverage_gaps(db: Session, expected_counts: dict[str, int] | None = None) -> list[dict]:
    """
    Compare active vehicle counts against expected counts per agency.
    Returns agencies where active vehicles are significantly below expected.

    Args:
        expected_counts: dict mapping agency -> expected minimum vehicle count.
                         If None, uses a 50% drop from recent average as threshold.
    """
    positions = get_latest_positions(db, seconds=120)
    agency_counts: dict[str, int] = {}
    for p in positions:
        agency_counts[p.agency] = agency_counts.get(p.agency, 0) + 1

    gaps = []
    if expected_counts:
        for agency, expected in expected_counts.items():
            actual = agency_counts.get(agency, 0)
            if actual < expected * 0.5:
                gaps.append({
                    "agency": agency,
                    "expected": expected,
                    "actual": actual,
                    "deficit_pct": round((1 - actual / max(expected, 1)) * 100, 1),
                })

    return gaps
