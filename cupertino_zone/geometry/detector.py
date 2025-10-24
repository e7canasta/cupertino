"""
Zone Detector Module
====================

Stateless detection logic - applies geometry to detections.

Design:
- Pure functions (no state)
- Dependency injection for external state (line crossings)
- Returns detection masks + updated state
- Thread-safe (no mutations)
"""

import numpy as np
import supervision as sv
from typing import Dict, Tuple

from cupertino_zone.geometry.shapes import PolygonZone, LineZone


class ZoneDetector:
    """
    Stateless detector for applying zone geometry to detections.

    Design Philosophy:
    - All methods are static (no instance state)
    - Pure functions where possible
    - External state injected (crossing tracker)
    - Returns results + updated state (functional style)
    """

    @staticmethod
    def detect_polygon(
        zone: PolygonZone,
        detections: sv.Detections,
        anchor: sv.Position = sv.Position.BOTTOM_CENTER
    ) -> np.ndarray:
        """
        Detect which detections are inside a polygon zone.

        Args:
            zone: Polygon geometry
            detections: YOLO detections with bounding boxes
            anchor: Which point of bbox to test (default: BOTTOM_CENTER)

        Returns:
            Boolean mask of shape (N,) where True = inside zone
        """
        if len(detections) == 0:
            return np.array([], dtype=bool)

        # Get anchor points from bounding boxes
        anchors = detections.get_anchors_coordinates(anchor=anchor)

        # Test each anchor against polygon
        mask = np.array([
            zone.contains_point((x, y))
            for x, y in anchors
        ], dtype=bool)

        return mask

    @staticmethod
    def detect_line_crossing(
        zone: LineZone,
        detections: sv.Detections,
        tracker_state: Dict[int, int],
        anchor: sv.Position = sv.Position.BOTTOM_CENTER
    ) -> Tuple[np.ndarray, np.ndarray, Dict[int, int]]:
        """
        Detect line crossings with directional tracking.

        This method is stateless - it receives tracker state and returns
        updated state (functional programming style).

        Args:
            zone: Line geometry
            detections: YOLO detections with tracker_id required
            tracker_state: External state {tracker_id: last_side}
                           where side is 1 (left), -1 (right), 0 (on line)
            anchor: Which point of bbox to test

        Returns:
            Tuple of:
            - crossed_in: Boolean mask where True = crossed left-to-right
            - crossed_out: Boolean mask where True = crossed right-to-left
            - updated_state: New tracker state dict

        Raises:
            ValueError: If detections lack tracker_id

        Design:
        - State is external (injected and returned)
        - No side effects on zone or detector
        - Thread-safe (no mutations)
        """
        # Validate tracker_id presence
        if detections.tracker_id is None:
            raise ValueError(
                "Line crossing detection requires tracker_id. "
                "Ensure detections are tracked (e.g., ByteTrack)"
            )

        if len(detections) == 0:
            return np.array([], dtype=bool), np.array([], dtype=bool), tracker_state

        # Get anchor points
        anchors = detections.get_anchors_coordinates(anchor=anchor)

        # Initialize result masks
        crossed_in = np.zeros(len(detections), dtype=bool)
        crossed_out = np.zeros(len(detections), dtype=bool)

        # Copy state for immutability (don't mutate input)
        new_state = tracker_state.copy()

        # Check each detection
        for idx, (tracker_id, (x, y)) in enumerate(zip(detections.tracker_id, anchors)):
            current_side = zone.get_side((x, y))

            # Check for crossing (requires previous state)
            if tracker_id in tracker_state:
                previous_side = tracker_state[tracker_id]

                # Detect crossing (side change)
                if previous_side != current_side and current_side != 0:
                    if current_side == 1:  # Moved to left (IN)
                        crossed_in[idx] = True
                    elif current_side == -1:  # Moved to right (OUT)
                        crossed_out[idx] = True

            # Update state
            new_state[tracker_id] = current_side

        return crossed_in, crossed_out, new_state
