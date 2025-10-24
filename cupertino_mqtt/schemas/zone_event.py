"""
Zone Event Message Schema
=========================

Bounded Context: Zone Event Data Structures

This module defines the schema for zone monitoring events published via MQTT.

Design:
- ZoneStats: Immutable statistics snapshot (like cupertino_zone.ZoneStats)
- ZoneEvent: Single zone event (enter/exit/crossing)
- ZoneEventMessage: Complete message with all zone states

Message Flow:
    ZoneMonitor → ZoneEvent → ZoneEventPublisher → MQTT → Subscriber → Visualizer
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
from .common import Timestamp


class ZoneType(str, Enum):
    """Zone type enumeration."""
    POLYGON = "polygon"
    LINE = "line"


class EventType(str, Enum):
    """Zone event type enumeration."""
    INSIDE = "inside"          # Objects inside polygon zone
    CROSSING = "crossing"      # Object crossed line zone


class CrossingDirection(str, Enum):
    """Line crossing direction."""
    IN = "in"
    OUT = "out"


@dataclass(frozen=True)
class ZoneStats:
    """
    Immutable zone statistics snapshot.

    Mirrors cupertino_zone.ZoneStats but optimized for MQTT serialization.

    For polygon zones:
        - total_in: Not applicable (None)
        - total_out: Not applicable (None)
        - current_count: Number of objects currently inside

    For line zones:
        - total_in: Total crossings in "in" direction
        - total_out: Total crossings in "out" direction
        - current_count: Not applicable (None)

    Attributes:
        total_in: Cumulative count entering (line zones)
        total_out: Cumulative count exiting (line zones)
        current_count: Current objects in zone (polygon zones)

    Example (Polygon):
        >>> stats = ZoneStats(total_in=None, total_out=None, current_count=2)

    Example (Line):
        >>> stats = ZoneStats(total_in=10, total_out=8, current_count=None)
    """
    total_in: Optional[int] = None
    total_out: Optional[int] = None
    current_count: Optional[int] = None

    def to_dict(self) -> Dict[str, Optional[int]]:
        """Serialize to JSON-compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Optional[int]]) -> 'ZoneStats':
        """Deserialize from dict."""
        return cls(
            total_in=data.get('total_in'),
            total_out=data.get('total_out'),
            current_count=data.get('current_count')
        )


@dataclass(frozen=True)
class ZoneEvent:
    """
    Single zone event (one zone's state).

    Represents the current state of one zone (polygon or line) after processing
    a frame.

    Attributes:
        zone_id: User-defined zone identifier (e.g., "entrance_zone")
        zone_type: Type of zone (polygon or line)
        event_type: Type of event (inside or crossing)
        stats: Statistical snapshot
        triggered_by: List of tracker IDs that triggered this event
        crossing_direction: Direction for line crossings (None for polygons)

    Invariants:
        - If zone_type == LINE, crossing_direction must be set
        - triggered_by is empty list if no objects involved

    Example (Polygon):
        >>> event = ZoneEvent(
        ...     zone_id="entrance_zone",
        ...     zone_type=ZoneType.POLYGON,
        ...     event_type=EventType.INSIDE,
        ...     stats=ZoneStats(current_count=2),
        ...     triggered_by=[1, 3]
        ... )

    Example (Line):
        >>> event = ZoneEvent(
        ...     zone_id="doorway_line",
        ...     zone_type=ZoneType.LINE,
        ...     event_type=EventType.CROSSING,
        ...     stats=ZoneStats(total_in=10, total_out=8),
        ...     triggered_by=[2],
        ...     crossing_direction=CrossingDirection.IN
        ... )
    """
    zone_id: str
    zone_type: ZoneType
    event_type: EventType
    stats: ZoneStats
    triggered_by: List[int] = field(default_factory=list)
    crossing_direction: Optional[CrossingDirection] = None

    def __post_init__(self):
        """Validate invariants."""
        if self.zone_type == ZoneType.LINE and self.crossing_direction is None:
            raise ValueError(
                "Line zones must have crossing_direction set"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        result = {
            'zone_id': self.zone_id,
            'zone_type': self.zone_type.value,
            'event_type': self.event_type.value,
            'stats': self.stats.to_dict(),
            'triggered_by': self.triggered_by
        }
        if self.crossing_direction is not None:
            result['crossing_direction'] = self.crossing_direction.value
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ZoneEvent':
        """Deserialize from dict.

        Args:
            data: Dictionary with zone event fields

        Returns:
            ZoneEvent instance

        Raises:
            ValueError: If required fields missing or invalid
        """
        try:
            crossing_dir = None
            if 'crossing_direction' in data:
                crossing_dir = CrossingDirection(data['crossing_direction'])

            return cls(
                zone_id=str(data['zone_id']),
                zone_type=ZoneType(data['zone_type']),
                event_type=EventType(data['event_type']),
                stats=ZoneStats.from_dict(data['stats']),
                triggered_by=list(data.get('triggered_by', [])),
                crossing_direction=crossing_dir
            )
        except KeyError as e:
            raise ValueError(f"Missing required ZoneEvent field: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid ZoneEvent data: {e}")

    @property
    def object_count(self) -> int:
        """Number of objects involved in this event."""
        return len(self.triggered_by)


@dataclass(frozen=True)
class ZoneEventMessage:
    """
    Complete zone event message for MQTT publication.

    Contains the state of all monitored zones for a single frame.

    Attributes:
        schema_version: Message schema version (for evolution)
        timestamp: ISO 8601 timestamp of message creation
        frame_id: Sequential frame number (correlates with DetectionMessage)
        source_id: Video source identifier
        zones: List of zone events (one per monitored zone)

    Example:
        >>> msg = ZoneEventMessage(
        ...     schema_version="1.0",
        ...     timestamp=Timestamp.now(),
        ...     frame_id=123,
        ...     source_id=0,
        ...     zones=[zone_event1, zone_event2]
        ... )
    """
    schema_version: str
    timestamp: Timestamp
    frame_id: int
    source_id: int
    zones: List[ZoneEvent] = field(default_factory=list)

    def __post_init__(self):
        """Validate invariants."""
        if self.frame_id < 0:
            raise ValueError(f"Frame ID must be >= 0, got {self.frame_id}")
        if self.source_id < 0:
            raise ValueError(f"Source ID must be >= 0, got {self.source_id}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            'schema_version': self.schema_version,
            'timestamp': self.timestamp.to_dict(),
            'frame_id': self.frame_id,
            'source_id': self.source_id,
            'zones': [zone.to_dict() for zone in self.zones]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ZoneEventMessage':
        """Deserialize from dict.

        Args:
            data: Dictionary with message fields

        Returns:
            ZoneEventMessage instance

        Raises:
            ValueError: If required fields missing or invalid
        """
        try:
            return cls(
                schema_version=str(data['schema_version']),
                timestamp=Timestamp(value=data['timestamp']),
                frame_id=int(data['frame_id']),
                source_id=int(data['source_id']),
                zones=[
                    ZoneEvent.from_dict(zone)
                    for zone in data.get('zones', [])
                ]
            )
        except KeyError as e:
            raise ValueError(f"Missing required ZoneEventMessage field: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid ZoneEventMessage data: {e}")

    @property
    def zone_count(self) -> int:
        """Number of zones in this message."""
        return len(self.zones)

    def get_zone_by_id(self, zone_id: str) -> Optional[ZoneEvent]:
        """Find zone event by ID.

        Args:
            zone_id: Zone identifier to search

        Returns:
            ZoneEvent if found, None otherwise
        """
        for zone in self.zones:
            if zone.zone_id == zone_id:
                return zone
        return None

    def get_zones_by_type(self, zone_type: ZoneType) -> List[ZoneEvent]:
        """Filter zones by type.

        Args:
            zone_type: Type to filter (POLYGON or LINE)

        Returns:
            List of matching zone events
        """
        return [zone for zone in self.zones if zone.zone_type == zone_type]
