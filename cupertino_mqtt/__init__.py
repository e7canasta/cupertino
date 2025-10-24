"""
Cupertino MQTT Communication Package
====================================

Bounded Context: Communication Protocol for Zone Monitoring

This package provides MQTT-based messaging for the Cupertino zone monitoring system,
enabling decoupled communication between the Stream Processor (inference) and
RTSP Visualizer (rendering).

Architecture:
- schemas/: Immutable data structures with type safety
- publishers/: Message producers (DetectionPublisher, ZoneEventPublisher)
- logging/: Structured JSON logging for observability

Design Philosophy:
- Cohesion > Location: Each module has one reason to change
- Type Safety: Leverage Python typing for correctness
- Immutability: Use frozen dataclasses for message DTOs
- Observability: Structured logs (JSON) for production queries

Public API
----------
Schemas:
    BBox, Timestamp
    Detection, DetectionMessage
    ZoneType, EventType, CrossingDirection
    ZoneStats, ZoneEvent, ZoneEventMessage

Publishers:
    DetectionPublisher, ZoneEventPublisher
    BasePublisher (for custom publishers)

Logging:
    LogEvent, StructuredLogger, create_logger

Example (Stream Processor):
    >>> from cupertino_mqtt import DetectionPublisher, create_logger
    >>> from cupertino_mqtt.schemas import Detection, DetectionMessage, BBox, Timestamp
    >>>
    >>> logger = create_logger("processor")
    >>> publisher = DetectionPublisher(
    ...     broker_host="localhost",
    ...     topic="cupertino/detections",
    ...     logger=logger
    ... )
    >>> publisher.connect()
    >>>
    >>> # Create detection message from YOLO output
    >>> det = Detection(tracker_id=1, class_name="person", confidence=0.95,
    ...                 bbox=BBox(x=100, y=200, width=50, height=100))
    >>> msg = DetectionMessage(
    ...     schema_version="1.0",
    ...     timestamp=Timestamp.now(),
    ...     frame_id=123,
    ...     source_id=0,
    ...     detections=[det]
    ... )
    >>> publisher.publish_detection(msg)

Example (Zone Events):
    >>> from cupertino_mqtt import ZoneEventPublisher
    >>> from cupertino_mqtt.schemas import ZoneEvent, ZoneEventMessage, ZoneType, EventType, ZoneStats
    >>>
    >>> zone_pub = ZoneEventPublisher(
    ...     broker_host="localhost",
    ...     topic="cupertino/zone_events",
    ...     logger=logger
    ... )
    >>> zone_pub.connect()
    >>>
    >>> zone_event = ZoneEvent(
    ...     zone_id="entrance",
    ...     zone_type=ZoneType.POLYGON,
    ...     event_type=EventType.INSIDE,
    ...     stats=ZoneStats(current_count=2),
    ...     triggered_by=[1, 3]
    ... )
    >>> zone_msg = ZoneEventMessage(
    ...     schema_version="1.0",
    ...     timestamp=Timestamp.now(),
    ...     frame_id=123,
    ...     source_id=0,
    ...     zones=[zone_event]
    ... )
    >>> zone_pub.publish_zone_event(zone_msg)
"""

# Version
__version__ = "1.0.0"

# Schemas
from .schemas import (
    BBox,
    Timestamp,
    Detection,
    DetectionMessage,
    ZoneType,
    EventType,
    CrossingDirection,
    ZoneStats,
    ZoneEvent,
    ZoneEventMessage,
)

# Publishers
from .publishers import (
    BasePublisher,
    DetectionPublisher,
    ZoneEventPublisher,
)

# Subscriber
from .subscriber import MessageSubscriber

# Logging
from .logging import (
    LogEvent,
    StructuredLogger,
    create_logger,
)

__all__ = [
    # Version
    '__version__',
    # Schemas - Common
    'BBox',
    'Timestamp',
    # Schemas - Detection
    'Detection',
    'DetectionMessage',
    # Schemas - Zone Events
    'ZoneType',
    'EventType',
    'CrossingDirection',
    'ZoneStats',
    'ZoneEvent',
    'ZoneEventMessage',
    # Publishers
    'BasePublisher',
    'DetectionPublisher',
    'ZoneEventPublisher',
    # Subscriber
    'MessageSubscriber',
    # Logging
    'LogEvent',
    'StructuredLogger',
    'create_logger',
]
