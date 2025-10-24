"""
Zone Detection Module
=====================

Bounded Context: Zone definition and object-in-zone detection.

Design:
- SRP: Un tipo de zona, una responsabilidad
- Usa supervision.geometry para polígonos (no reinventar)
- Pure logic: detección sin side effects

Dependencies:
- supervision (geometry, Point)
- numpy (array operations)
"""

import numpy as np
import supervision as sv
from typing import Protocol


class ZoneMonitor(Protocol):
    """Protocol for zone monitors (interface)."""

    def is_inside(self, point: sv.Point) -> bool:
        """Check if a point is inside the zone."""
        ...

    def trigger(self, detections: sv.Detections) -> np.ndarray:
        """
        Check which detections are inside the zone.

        Returns:
            Boolean mask indicating which detections are in zone.
        """
        ...


class PolygonZoneMonitor:
    """
    Monitors objects within a polygon area.

    Design: KISS - wraps supervision polygon checking with our domain logic.
    """

    def __init__(self, polygon: np.ndarray, frame_resolution_wh: tuple[int, int]):
        """
        Args:
            polygon: Nx2 array of (x, y) coordinates defining polygon vertices
            frame_resolution_wh: (width, height) of video frame
        """
        self.polygon = polygon
        self.frame_resolution_wh = frame_resolution_wh
        self.current_count = 0

        # Create mask for fast point-in-polygon checks
        self._mask = self._create_mask()

    def _create_mask(self) -> np.ndarray:
        """Create binary mask from polygon for fast lookups."""
        mask = np.zeros((self.frame_resolution_wh[1], self.frame_resolution_wh[0]), dtype=np.uint8)
        cv2_polygon = self.polygon.reshape((-1, 1, 2)).astype(np.int32)

        import cv2
        cv2.fillPoly(mask, [cv2_polygon], color=1)
        return mask.astype(bool)

    def is_inside(self, point: sv.Point) -> bool:
        """Check if a single point is inside the polygon."""
        x, y = int(point.x), int(point.y)

        # Bounds check
        if not (0 <= x < self.frame_resolution_wh[0] and 0 <= y < self.frame_resolution_wh[1]):
            return False

        return bool(self._mask[y, x])

    def trigger(self, detections: sv.Detections) -> np.ndarray:
        """
        Check which detections are inside the polygon.

        Uses bottom-center anchor (typical for people/vehicles).
        """
        if len(detections) == 0:
            self.current_count = 0
            return np.array([], dtype=bool)

        # Get bottom-center points of bounding boxes
        anchors = detections.get_anchors_coordinates(anchor=sv.Position.BOTTOM_CENTER)

        # Check each anchor against mask
        is_in_zone = np.array([
            self.is_inside(sv.Point(x=x, y=y))
            for x, y in anchors
        ], dtype=bool)

        self.current_count = int(np.sum(is_in_zone))
        return is_in_zone


class LineZoneMonitor:
    """
    Monitors objects crossing a line (directional counting).

    Design: Simplified vs supervision - only tracks crossings, not full history.
    """

    def __init__(self, start: sv.Point, end: sv.Point):
        """
        Args:
            start: Line start point
            end: Line end point
        """
        self.start = start
        self.end = end

        # Line vector for side determination
        self._vector = np.array([end.x - start.x, end.y - start.y])

        # Crossing counters
        self.in_count = 0
        self.out_count = 0

        # Track last known side per object ID
        self._last_side: dict[int, bool] = {}  # True = left, False = right

    def _get_side(self, point: sv.Point) -> bool:
        """
        Determine which side of the line a point is on.

        Returns:
            True if left of line, False if right
        """
        # Vector from line start to point
        to_point = np.array([point.x - self.start.x, point.y - self.start.y])

        # Cross product determines side
        cross = np.cross(self._vector, to_point)
        return cross > 0

    def trigger(self, detections: sv.Detections) -> tuple[np.ndarray, np.ndarray]:
        """
        Check for line crossings.

        Returns:
            Tuple of (crossed_in, crossed_out) boolean masks
        """
        if len(detections) == 0:
            return np.array([], dtype=bool), np.array([], dtype=bool)

        # Require tracker_id for crossing detection
        if detections.tracker_id is None:
            raise ValueError("LineZoneMonitor requires tracked detections (tracker_id)")

        # Get bottom-center points
        anchors = detections.get_anchors_coordinates(anchor=sv.Position.BOTTOM_CENTER)

        crossed_in = np.zeros(len(detections), dtype=bool)
        crossed_out = np.zeros(len(detections), dtype=bool)

        for idx, (tracker_id, (x, y)) in enumerate(zip(detections.tracker_id, anchors)):
            point = sv.Point(x=x, y=y)
            current_side = self._get_side(point)

            # Check if crossed
            if tracker_id in self._last_side:
                previous_side = self._last_side[tracker_id]

                if previous_side != current_side:
                    # Crossing detected
                    if current_side:  # Moved to left (crossing IN)
                        self.in_count += 1
                        crossed_in[idx] = True
                    else:  # Moved to right (crossing OUT)
                        self.out_count += 1
                        crossed_out[idx] = True

            # Update last known side
            self._last_side[tracker_id] = current_side

        return crossed_in, crossed_out
