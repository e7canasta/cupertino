"""
Zone Monitor Registry - Thread-safe zone management.

This module provides the ZoneMonitorRegistry class which manages a collection
of zones in a thread-safe manner. It supports hot-reconfiguration via MQTT commands.

REFACTORED for cupertino_zone v2.0 API:
- Separates geometry (PolygonZone/LineZone) from analytics (Counter/Tracker)
- Uses ZoneDetector for stateless detection
- Maintains backward-compatible API

Thread Safety:
- Uses threading.Lock for protecting zone dict mutations
- Snapshot pattern for trigger() to minimize lock holding time
- Zone objects are immutable (frozen dataclass)
"""

import threading
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np
import supervision as sv

# New cupertino_zone API (v2.0)
from cupertino_zone import PolygonZone, LineZone, ZoneDetector
from cupertino_zone.analytics import ZoneCounter, ZoneStats, CrossingTracker


@dataclass
class ManagedZone:
    """
    Encapsulates zone geometry, counter, and tracker for registry management.

    Design:
    - Separation of concerns: geometry + analytics
    - Type-safe: stores zone type explicitly
    - Tracker only for line zones
    """

    zone_id: str
    zone: PolygonZone | LineZone
    counter: ZoneCounter
    tracker: CrossingTracker | None = None  # Only for LineZone
    enabled: bool = True

    @property
    def zone_type(self) -> str:
        """Get zone type string."""
        if isinstance(self.zone, PolygonZone):
            return "polygon"
        elif isinstance(self.zone, LineZone):
            return "line"
        else:
            return "unknown"

    def get_stats(self) -> ZoneStats:
        """Get current statistics snapshot."""
        return self.counter.get_stats()


class ZoneMonitorRegistry:
    """
    Thread-safe registry for zone monitors (REFACTORED for v2.0 API).

    This class manages a collection of zones with separation of concerns:
    - Geometry layer (PolygonZone/LineZone)
    - Analytics layer (ZoneCounter, CrossingTracker)

    The trigger() method uses a snapshot pattern to minimize lock contention:
    1. Acquire lock
    2. Create snapshot of enabled zones
    3. Release lock
    4. Process detections (long operation)

    Thread Safety Guarantees:
    - add_zone(), remove_zone(), update_zone(): Write operations (acquire lock)
    - enable_zone(), disable_zone(): Write operations (acquire lock)
    - trigger(): Read operation with snapshot (acquire lock briefly)
    - list_zones(), get_zone_info(): Read operations (acquire lock briefly)

    Usage (NEW API):
        registry = ZoneMonitorRegistry()

        # Add polygon zone (thread-safe)
        polygon = PolygonZone(vertices=np.array([[100, 200], [500, 200]]),
                              frame_resolution_wh=(1920, 1080))
        registry.add_polygon_zone("entrance", polygon)

        # Add line zone (thread-safe)
        line = LineZone(start=(0, 500), end=(1920, 500))
        registry.add_line_zone("crossing", line)

        # Trigger zones (thread-safe, minimal lock time)
        results = registry.trigger(detections)
        # results = {
        #     "entrance": (mask, ZoneStats),
        #     "crossing": (crossed_in, crossed_out, ZoneStats)
        # }
    """

    def __init__(self):
        """Initialize empty registry."""
        self._managed_zones: Dict[str, ManagedZone] = {}
        self._lock = threading.Lock()

    def add_polygon_zone(self, zone_id: str, zone: PolygonZone) -> None:
        """
        Add a polygon zone to the registry.

        Args:
            zone_id: Unique identifier for the zone
            zone: PolygonZone instance

        Raises:
            ValueError: If zone_id already exists

        Thread-safe: Acquires lock for write operation.
        """
        managed_zone = ManagedZone(
            zone_id=zone_id,
            zone=zone,
            counter=ZoneCounter(zone_id=zone_id),
            tracker=None,  # Polygon zones don't need tracker
            enabled=True
        )
        
        with self._lock:
            if zone_id in self._managed_zones:
                raise ValueError(f"Zone '{zone_id}' already exists")
            self._managed_zones[zone_id] = managed_zone

    def add_line_zone(self, zone_id: str, zone: LineZone) -> None:
        """
        Add a line zone to the registry.

        Args:
            zone_id: Unique identifier for the zone
            zone: LineZone instance

        Raises:
            ValueError: If zone_id already exists

        Thread-safe: Acquires lock for write operation.
        """
        managed_zone = ManagedZone(
            zone_id=zone_id,
            zone=zone,
            counter=ZoneCounter(zone_id=zone_id),
            tracker=CrossingTracker(),  # Line zones need tracker
            enabled=True
        )
        
        with self._lock:
            if zone_id in self._managed_zones:
                raise ValueError(f"Zone '{zone_id}' already exists")
            self._managed_zones[zone_id] = managed_zone

    def add_zone(self, zone_id: str, zone: PolygonZone | LineZone) -> None:
        """
        Add a zone to the registry (auto-detects type).

        Args:
            zone_id: Unique identifier for the zone
            zone: PolygonZone or LineZone instance

        Raises:
            ValueError: If zone_id already exists or invalid zone type

        Thread-safe: Acquires lock for write operation.
        """
        if isinstance(zone, PolygonZone):
            self.add_polygon_zone(zone_id, zone)
        elif isinstance(zone, LineZone):
            self.add_line_zone(zone_id, zone)
        else:
            raise ValueError(f"Invalid zone type: {type(zone)}")

    def remove_zone(self, zone_id: str) -> None:
        """
        Remove a zone from the registry.

        Args:
            zone_id: Zone identifier to remove

        Raises:
            KeyError: If zone_id does not exist

        Thread-safe: Acquires lock for write operation.
        """
        with self._lock:
            if zone_id not in self._managed_zones:
                raise KeyError(f"Zone '{zone_id}' not found")
            del self._managed_zones[zone_id]

    def update_zone(self, zone_id: str, zone: PolygonZone | LineZone) -> None:
        """
        Update an existing zone (replaces geometry, resets counter).

        Args:
            zone_id: Zone identifier to update
            zone: New PolygonZone or LineZone instance

        Raises:
            KeyError: If zone_id does not exist
            ValueError: If zone type doesn't match existing zone

        Thread-safe: Acquires lock for write operation.
        """
        with self._lock:
            if zone_id not in self._managed_zones:
                raise KeyError(f"Zone '{zone_id}' not found")

            old_managed = self._managed_zones[zone_id]
            old_enabled = old_managed.enabled

            # Verify type consistency
            if type(old_managed.zone) != type(zone):
                raise ValueError(
                    f"Cannot change zone type from {type(old_managed.zone).__name__} "
                    f"to {type(zone).__name__}"
                )

            # Create new managed zone with fresh counter/tracker
            if isinstance(zone, PolygonZone):
                new_managed = ManagedZone(
                    zone_id=zone_id,
                    zone=zone,
                    counter=ZoneCounter(zone_id=zone_id),
                    tracker=None,
                    enabled=old_enabled
                )
            else:  # LineZone
                new_managed = ManagedZone(
                    zone_id=zone_id,
                    zone=zone,
                    counter=ZoneCounter(zone_id=zone_id),
                    tracker=CrossingTracker(),
                    enabled=old_enabled
                )

            self._managed_zones[zone_id] = new_managed

    def enable_zone(self, zone_id: str) -> None:
        """
        Enable a zone.

        Args:
            zone_id: Zone identifier to enable

        Raises:
            KeyError: If zone_id does not exist

        Thread-safe: Acquires lock for write operation.
        """
        with self._lock:
            if zone_id not in self._managed_zones:
                raise KeyError(f"Zone '{zone_id}' not found")
            self._managed_zones[zone_id].enabled = True

    def disable_zone(self, zone_id: str) -> None:
        """
        Disable a zone.

        Args:
            zone_id: Zone identifier to disable

        Raises:
            KeyError: If zone_id does not exist

        Thread-safe: Acquires lock for write operation.
        """
        with self._lock:
            if zone_id not in self._managed_zones:
                raise KeyError(f"Zone '{zone_id}' not found")
            self._managed_zones[zone_id].enabled = False

    def trigger(
        self,
        detections: sv.Detections,
        class_names: Dict[int, str] | None = None
    ) -> Dict[str, Tuple[np.ndarray, ZoneStats]]:
        """
        Trigger all enabled zones with detections (NEW API v2.0).

        This method uses a snapshot pattern to minimize lock holding time:
        1. Acquire lock and create snapshot of enabled zones
        2. Release lock
        3. Process detections (potentially slow operation)
        4. Update counters and get stats

        Args:
            detections: Supervision Detections object
            class_names: Optional mapping {class_id: name} for classwise counting

        Returns:
            Dictionary mapping zone_id to (detection_mask, stats):
            - For polygon zones: mask is boolean array (in zone or not)
            - For line zones: mask is tuple (crossed_in, crossed_out)
            - stats is ZoneStats with counts

        Thread-safe: Minimizes lock contention by using snapshot pattern.

        Example:
            detections = sv.Detections(...)
            results = registry.trigger(detections, class_names={0: "car", 1: "person"})
            # results = {
            #     "entrance": (np.array([True, False, True, ...]), ZoneStats(...)),
            #     "crossing": ((in_mask, out_mask), ZoneStats(...))
            # }
        """
        # Snapshot pattern: acquire lock, copy references, release
        with self._lock:
            zones_snapshot = [
                managed_zone
                for managed_zone in self._managed_zones.values()
                if managed_zone.enabled
            ]

        # Process detections outside lock (long operation)
        results = {}
        
        for managed_zone in zones_snapshot:
            if isinstance(managed_zone.zone, PolygonZone):
                # Detect which objects are in polygon
                mask = ZoneDetector.detect_polygon(managed_zone.zone, detections)
                
                # Update counter
                managed_zone.counter.update_polygon(mask, detections, class_names)
                stats = managed_zone.counter.get_stats()
                
                results[managed_zone.zone_id] = (mask, stats)
                
            elif isinstance(managed_zone.zone, LineZone):
                # Detect line crossings (requires tracker state)
                if managed_zone.tracker is None:
                    raise RuntimeError(
                        f"Line zone '{managed_zone.zone_id}' missing tracker"
                    )
                
                crossed_in, crossed_out, new_state = ZoneDetector.detect_line_crossing(
                    managed_zone.zone, 
                    detections, 
                    managed_zone.tracker.state
                )
                
                # Update tracker state
                managed_zone.tracker.state = new_state
                
                # Update counter
                managed_zone.counter.update_line(
                    crossed_in, crossed_out, detections, class_names
                )
                stats = managed_zone.counter.get_stats()
                
                results[managed_zone.zone_id] = ((crossed_in, crossed_out), stats)

        return results

    def list_zones(self) -> Dict[str, bool]:
        """
        List all zones and their enabled status.

        Returns:
            Dictionary mapping zone_id to enabled status.

        Thread-safe: Acquires lock for read operation.
        """
        with self._lock:
            return {
                zone_id: managed.enabled
                for zone_id, managed in self._managed_zones.items()
            }

    def get_zone_info(self, zone_id: str) -> Dict[str, any]:
        """
        Get information about a specific zone.

        Args:
            zone_id: Zone identifier

        Returns:
            Dictionary with zone information:
            - zone_type: "polygon" or "line"
            - enabled: bool
            - coordinates: List of points
            - stats: Current statistics (ZoneStats)

        Raises:
            KeyError: If zone_id does not exist

        Thread-safe: Acquires lock for read operation.
        """
        with self._lock:
            if zone_id not in self._managed_zones:
                raise KeyError(f"Zone '{zone_id}' not found")

            managed = self._managed_zones[zone_id]

            # Extract coordinates based on zone type
            if isinstance(managed.zone, PolygonZone):
                coordinates = managed.zone.vertices.tolist()
            elif isinstance(managed.zone, LineZone):
                coordinates = [
                    list(managed.zone.start),
                    list(managed.zone.end)
                ]
            else:
                coordinates = None

            return {
                "zone_type": managed.zone_type,
                "enabled": managed.enabled,
                "coordinates": coordinates,
                "stats": managed.get_stats(),
            }

    def get_zone_stats(self, zone_id: str) -> ZoneStats:
        """
        Get current statistics for a zone.

        Args:
            zone_id: Zone identifier

        Returns:
            ZoneStats snapshot

        Raises:
            KeyError: If zone_id does not exist

        Thread-safe: Acquires lock for read operation.
        """
        with self._lock:
            if zone_id not in self._managed_zones:
                raise KeyError(f"Zone '{zone_id}' not found")
            return self._managed_zones[zone_id].get_stats()

    def clear(self) -> None:
        """
        Remove all zones from the registry.

        Thread-safe: Acquires lock for write operation.
        """
        with self._lock:
            self._managed_zones.clear()

    def count(self) -> int:
        """
        Get the number of zones in the registry.

        Returns:
            Number of zones (enabled + disabled).

        Thread-safe: Acquires lock for read operation.
        """
        with self._lock:
            return len(self._managed_zones)
