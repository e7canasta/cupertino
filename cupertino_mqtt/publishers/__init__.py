"""
MQTT Publishers
==============

Bounded Context: Message Production

This module provides publishers for sending detection and zone event messages
to MQTT broker.

Design:
- BasePublisher: Abstract base with connection management
- DetectionPublisher: Publishes detection messages
- ZoneEventPublisher: Publishes zone event messages
- Separation of concerns: Publishers format, broker publishes

Public API
----------
    BasePublisher: Abstract publisher (for custom publishers)
    DetectionPublisher: Detection message publisher
    ZoneEventPublisher: Zone event message publisher

Example:
    >>> from cupertino_mqtt.publishers import DetectionPublisher
    >>> from cupertino_mqtt.logging import create_logger
    >>>
    >>> logger = create_logger("processor")
    >>> publisher = DetectionPublisher(
    ...     broker_host="localhost",
    ...     broker_port=1883,
    ...     topic="cupertino/detections",
    ...     logger=logger
    ... )
    >>> publisher.connect()
    >>> publisher.publish_detection(detection_message)
"""

from .base import BasePublisher
from .detection import DetectionPublisher
from .zone_event import ZoneEventPublisher

__all__ = [
    'BasePublisher',
    'DetectionPublisher',
    'ZoneEventPublisher',
]
