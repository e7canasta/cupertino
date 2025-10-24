"""
Cupertino MQTT Schemas
=====================

Bounded Context: Data Structures

This module defines immutable, typed data structures for MQTT messages.

Design:
- Frozen dataclasses (immutability)
- Type hints for all fields (mypy compatible)
- to_dict() for JSON serialization
- from_dict() for deserialization
- Schema versioning for evolution

Public API
----------
Common Types:
    BBox: Bounding box with validation
    Timestamp: ISO 8601 timestamp wrapper

Detection Types:
    Detection: Single object detection
    DetectionMessage: Complete detection message

Zone Event Types:
    ZoneType: Enum (POLYGON, LINE)
    EventType: Enum (INSIDE, CROSSING)
    CrossingDirection: Enum (IN, OUT)
    ZoneStats: Immutable statistics snapshot
    ZoneEvent: Single zone event
    ZoneEventMessage: Complete zone event message

Example:
    >>> from cupertino_mqtt.schemas import Detection, BBox, DetectionMessage
    >>> det = Detection(
    ...     tracker_id=1,
    ...     class_name="person",
    ...     confidence=0.95,
    ...     bbox=BBox(x=100, y=200, width=50, height=100)
    ... )
"""

from .common import BBox, Timestamp
from .detection import Detection, DetectionMessage
from .zone_event import (
    ZoneType,
    EventType,
    CrossingDirection,
    ZoneStats,
    ZoneEvent,
    ZoneEventMessage,
)

__all__ = [
    # Common types
    'BBox',
    'Timestamp',
    # Detection types
    'Detection',
    'DetectionMessage',
    # Zone event types
    'ZoneType',
    'EventType',
    'CrossingDirection',
    'ZoneStats',
    'ZoneEvent',
    'ZoneEventMessage',
]
