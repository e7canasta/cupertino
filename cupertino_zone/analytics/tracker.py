"""
Crossing Tracker Module
=======================

Stateful tracker for line crossing detection.

Design:
- Encapsulates tracker state (tracker_id -> last_side)
- Clean API: update() returns crossing events
- Thread-safe via encapsulation (caller must synchronize)
- Can be reset or cleared
"""

from typing import Dict


class CrossingTracker:
    """
    Tracks object positions relative to a line for crossing detection.

    Design Philosophy:
    - Single Responsibility: Only track side history
    - Stateful but encapsulated
    - Works with ZoneDetector.detect_line_crossing()

    State:
        {tracker_id: last_side} where side is:
        - 1: left of line
        - -1: right of line
        - 0: on line

    Usage:
        tracker = CrossingTracker()

        # Each frame
        crossed_in, crossed_out, tracker.state = ZoneDetector.detect_line_crossing(
            zone, detections, tracker.state
        )
    """

    def __init__(self):
        """Initialize empty tracker state."""
        self._state: Dict[int, int] = {}

    @property
    def state(self) -> Dict[int, int]:
        """
        Get current tracker state.

        Returns:
            Dictionary mapping tracker_id to last_side
        """
        return self._state

    @state.setter
    def state(self, new_state: Dict[int, int]) -> None:
        """
        Update tracker state.

        Args:
            new_state: New state from detector
        """
        self._state = new_state

    def reset(self) -> None:
        """Clear all tracked objects."""
        self._state.clear()

    def prune(self, active_tracker_ids: set[int]) -> None:
        """
        Remove stale tracker IDs not in active set.

        Useful for memory management when objects leave the scene.

        Args:
            active_tracker_ids: Set of currently active tracker IDs
        """
        stale_ids = set(self._state.keys()) - active_tracker_ids
        for tracker_id in stale_ids:
            del self._state[tracker_id]

    def __len__(self) -> int:
        """Return number of tracked objects."""
        return len(self._state)

    def __repr__(self) -> str:
        """Human-readable representation."""
        return f"CrossingTracker(tracked={len(self._state)})"

