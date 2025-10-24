"""
Zone Counter Module
===================

Bounded Context: Object counting and statistics tracking.

Design:
- SRP: Solo maneja conteo y estadísticas
- Inmutable: Genera reportes sin mutar estado externo
- Testeable: Pure functions para agregaciones

Dependencies:
- supervision (Detections)
- typing (type hints)
"""

from dataclasses import dataclass
from typing import Dict
import supervision as sv


@dataclass
class ZoneStats:
    """Immutable statistics for a zone."""

    total_count: int
    count_per_class: Dict[int, int]

    def __str__(self) -> str:
        return f"Total: {self.total_count}"


class ZoneCounter:
    """
    Tracks and aggregates zone statistics.

    Design: Stateful accumulator for zone events.
    """

    def __init__(self, class_names: Dict[int, str] | None = None):
        """
        Args:
            class_names: Optional mapping of class_id -> name
        """
        self.class_names = class_names or {}
        self._count_per_class: Dict[int, int] = {}
        self._total_count = 0

    def update(self, detections: sv.Detections, in_zone_mask: sv.Detections) -> None:
        """
        Update counts based on detections in zone.

        Args:
            detections: All detections
            in_zone_mask: Boolean mask of which detections are in zone
        """
        # Filter to detections in zone
        zone_detections = detections[in_zone_mask]

        # Update total
        self._total_count = len(zone_detections)

        # Update per-class counts
        self._count_per_class.clear()
        if zone_detections.class_id is not None:
            for class_id in zone_detections.class_id:
                self._count_per_class[class_id] = self._count_per_class.get(class_id, 0) + 1

    def get_stats(self) -> ZoneStats:
        """Get current statistics snapshot."""
        return ZoneStats(
            total_count=self._total_count,
            count_per_class=dict(self._count_per_class),
        )

    def reset(self) -> None:
        """Reset all counters."""
        self._count_per_class.clear()
        self._total_count = 0
