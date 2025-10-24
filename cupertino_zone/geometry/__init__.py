"""
Geometry Layer
==============

Bounded Context: Pure geometric shapes and spatial queries.

Responsibilities:
- Shape representation (immutable)
- Point-in-polygon tests
- Line side calculations
- NO state, NO counting, NO visualization

Design Philosophy:
- Pure functions where possible
- Immutable data structures
- Fail-fast validation
- Zero side effects
"""

from cupertino_zone.geometry.shapes import PolygonZone, LineZone
from cupertino_zone.geometry.detector import ZoneDetector

__all__ = [
    "PolygonZone",
    "LineZone",
    "ZoneDetector",
]
