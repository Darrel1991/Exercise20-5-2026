"""
Disaster zone analysis — Phase 3 stub.
Will provide:
- Polygon-based vehicle filtering (vehicles within a drawn zone)
- Mass stoppage alerting
- Flood zone GeoJSON overlay integration
"""

import logging

logger = logging.getLogger(__name__)


def vehicles_in_polygon(positions: list[dict], polygon: list[tuple[float, float]]) -> list[dict]:
    """
    Filter vehicles that fall within a given polygon.
    Uses ray-casting point-in-polygon algorithm.

    Args:
        positions: list of dicts with 'latitude' and 'longitude' keys
        polygon: list of (lat, lng) tuples defining the zone boundary
    """
    def _point_in_polygon(lat: float, lng: float, poly: list[tuple[float, float]]) -> bool:
        n = len(poly)
        inside = False
        j = n - 1
        for i in range(n):
            yi, xi = poly[i]
            yj, xj = poly[j]
            if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    return [p for p in positions if _point_in_polygon(p["latitude"], p["longitude"], polygon)]
