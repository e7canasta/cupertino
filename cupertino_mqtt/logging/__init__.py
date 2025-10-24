"""
Structured Logging for Cupertino MQTT
=====================================

Bounded Context: Observability

This module provides JSON-structured logging for production observability.

Design:
- JSON output (parseable by ELK, CloudWatch, Loki)
- Typed events (enums prevent typos)
- Contextual metadata (frame_id, zone_id, etc.)
- Thread-safe

Public API
----------
    LogEvent: Typed event names (enum)
    StructuredLogger: JSON logger implementation
    create_logger: Factory function

Example:
    >>> from cupertino_mqtt.logging import StructuredLogger, LogEvent
    >>> logger = StructuredLogger(component="processor")
    >>> logger.info(
    ...     event=LogEvent.DETECTION_PROCESSED,
    ...     message="Processed 3 detections",
    ...     metadata={'frame_id': 123, 'detection_count': 3}
    ... )

Output:
    {
        "timestamp": "2025-10-24T15:30:45.123456",
        "level": "INFO",
        "component": "processor",
        "event": "detection.processed",
        "message": "Processed 3 detections",
        "metadata": {"frame_id": 123, "detection_count": 3}
    }
"""

from .events import LogEvent
from .structured import StructuredLogger, create_logger

__all__ = [
    'LogEvent',
    'StructuredLogger',
    'create_logger',
]
