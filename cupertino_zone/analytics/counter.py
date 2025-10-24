"""
Zone Counter Module
===================

Stateful accumulator for zone statistics.

Design:
- Mutable state (counters)
- Immutable snapshots (ZoneStats)
- Classwise counting support
- Reset capability
"""

import supervision as sv
import numpy as np
from dataclasses import dataclass, field
from typing import Dict
from collections import defaultdict


@dataclass(frozen=True)
class ZoneStats:
    """
    Immutable statistics snapshot for a zone.

    Design:
    - Frozen dataclass (thread-safe read)
    - Value object (no identity)
    - Can be serialized to JSON/MQTT
    """

    zone_id: str
    current_count: int = 0
    total_entered: int = 0
    total_exited: int = 0
    classwise_counts: Dict[str, int] = field(default_factory=dict)

    def __str__(self) -> str:
        """Human-readable representation."""
        if self.total_entered > 0 or self.total_exited > 0:
            return f"{self.zone_id}: IN={self.total_entered}, OUT={self.total_exited}"
        else:
            return f"{self.zone_id}: Count={self.current_count}"


class ZoneCounter:
    """
    Stateful counter for zone statistics.

    Design:
    - Mutable accumulators (private state)
    - Public immutable snapshots (get_stats())
    - Supports both polygon (presence) and line (crossing) counting
    - Thread-safety via encapsulation (caller must synchronize if multi-threaded)

    Usage:
        counter = ZoneCounter(zone_id="entrance")

        # Polygon zone update
        counter.update_polygon(mask, detections, class_names)

        # Line zone update
        counter.update_line(crossed_in, crossed_out, detections, class_names)

        # Get snapshot
        stats = counter.get_stats()  # Immutable
    """

    def __init__(self, zone_id: str):
        """
        Initialize counter for a zone.

        Args:
            zone_id: Unique identifier for this zone
        """
        self.zone_id = zone_id

        # Polygon counting state
        self._current_count = 0

        # Line counting state
        self._total_entered = 0
        self._total_exited = 0

        # Classwise counts (shared by both modes)
        self._classwise_counts: Dict[str, int] = defaultdict(int)

    def update_polygon(
        self,
        mask: np.ndarray,
        detections: sv.Detections,
        class_names: Dict[int, str] | None = None
    ) -> None:
        """
        Update counter for polygon zone (presence counting).

        Args:
            mask: Boolean mask from detector (which detections are inside)
            detections: All detections
            class_names: Optional mapping {class_id: name}
        """
        # Current count = sum of mask
        self._current_count = int(mask.sum())

        # Update classwise counts (reset each frame for polygon)
        self._classwise_counts.clear()

        if detections.class_id is not None and len(mask) > 0:
            # Filter to detections in zone
            in_zone_indices = np.where(mask)[0]

            for idx in in_zone_indices:
                class_id = detections.class_id[idx]
                class_name = class_names.get(class_id, f"class_{class_id}") if class_names else f"class_{class_id}"
                self._classwise_counts[class_name] += 1

    def update_line(
        self,
        crossed_in: np.ndarray,
        crossed_out: np.ndarray,
        detections: sv.Detections,
        class_names: Dict[int, str] | None = None
    ) -> None:
        """
        Update counter for line zone (crossing counting).

        Args:
            crossed_in: Boolean mask of detections that crossed IN this frame
            crossed_out: Boolean mask of detections that crossed OUT this frame
            detections: All detections
            class_names: Optional mapping {class_id: name}
        """
        # Accumulate total crossings
        self._total_entered += int(crossed_in.sum())
        self._total_exited += int(crossed_out.sum())

        # Update classwise counts (accumulative for line zones)
        if detections.class_id is not None and len(crossed_in) > 0:
            # Detections that crossed IN
            in_indices = np.where(crossed_in)[0]
            for idx in in_indices:
                class_id = detections.class_id[idx]
                class_name = class_names.get(class_id, f"class_{class_id}") if class_names else f"class_{class_id}"
                self._classwise_counts[f"{class_name}_IN"] += 1

            # Detections that crossed OUT
            out_indices = np.where(crossed_out)[0]
            for idx in out_indices:
                class_id = detections.class_id[idx]
                class_name = class_names.get(class_id, f"class_{class_id}") if class_names else f"class_{class_id}"
                self._classwise_counts[f"{class_name}_OUT"] += 1

    def get_stats(self) -> ZoneStats:
        """
        Get immutable statistics snapshot.

        Returns:
            Frozen ZoneStats with current state
        """
        return ZoneStats(
            zone_id=self.zone_id,
            current_count=self._current_count,
            total_entered=self._total_entered,
            total_exited=self._total_exited,
            classwise_counts=dict(self._classwise_counts)  # Copy dict
        )

    def reset(self) -> None:
        """Reset all counters to zero."""
        self._current_count = 0
        self._total_entered = 0
        self._total_exited = 0
        self._classwise_counts.clear()
