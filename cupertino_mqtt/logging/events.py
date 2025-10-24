"""
Structured Log Event Types
==========================

Bounded Context: Observability Event Taxonomy

This module defines typed event names for structured logging.

Design:
- Enum-based (prevents typos, enables autocomplete)
- Hierarchical naming (namespace.category.action)
- Searchable in log aggregators (Elasticsearch, CloudWatch Insights)

Event Naming Convention:
    <component>.<category>.<action>

    component: mqtt, detection, zone, error
    category: connected, publish, triggered
    action: success, failed, updated

Example Log Query (CloudWatch Insights):
    fields @timestamp, event, message, metadata.frame_id
    | filter event = "mqtt.publish.success"
    | stats count() by bin(5m)
"""

from enum import Enum


class LogEvent(str, Enum):
    """
    Typed log event names for structured logging.

    Each event represents a discrete, meaningful action in the system.
    Use these events for metrics, alerting, and debugging.

    Categories:
    - mqtt.*: MQTT broker interactions
    - detection.*: Detection processing
    - zone.*: Zone monitoring events
    - error.*: Error conditions
    """

    # ========== MQTT Events ==========
    MQTT_CONNECTED = "mqtt.connected"
    """MQTT broker connection established."""

    MQTT_DISCONNECTED = "mqtt.disconnected"
    """MQTT broker connection lost."""

    MQTT_PUBLISH_SUCCESS = "mqtt.publish.success"
    """Message successfully published to broker."""

    MQTT_PUBLISH_FAILED = "mqtt.publish.failed"
    """Message publication failed."""

    MQTT_RECONNECTING = "mqtt.reconnecting"
    """Attempting to reconnect to broker."""

    # ========== Detection Events ==========
    DETECTION_PROCESSED = "detection.processed"
    """Detections processed from YOLO inference."""

    DETECTION_SERIALIZED = "detection.serialized"
    """Detection message serialized to JSON."""

    DETECTION_RECEIVED = "detection.received"
    """Detection message received by subscriber."""

    # ========== Zone Events ==========
    ZONE_TRIGGERED = "zone.triggered"
    """Zone event triggered (enter/exit/crossing)."""

    ZONE_STATS_UPDATED = "zone.stats_updated"
    """Zone statistics updated."""

    ZONE_EVENT_SERIALIZED = "zone.event.serialized"
    """Zone event message serialized to JSON."""

    ZONE_EVENT_RECEIVED = "zone.event.received"
    """Zone event message received by subscriber."""

    # ========== Error Events ==========
    SERIALIZATION_ERROR = "error.serialization"
    """Failed to serialize message to JSON."""

    DESERIALIZATION_ERROR = "error.deserialization"
    """Failed to deserialize message from JSON."""

    SCHEMA_VALIDATION_ERROR = "error.schema_validation"
    """Message failed schema validation."""

    MQTT_CONNECTION_ERROR = "error.mqtt_connection"
    """Failed to connect to MQTT broker."""

    MQTT_PUBLISH_ERROR = "error.mqtt_publish"
    """Error during message publication."""


# Event categories for filtering
MQTT_EVENTS = {
    LogEvent.MQTT_CONNECTED,
    LogEvent.MQTT_DISCONNECTED,
    LogEvent.MQTT_PUBLISH_SUCCESS,
    LogEvent.MQTT_PUBLISH_FAILED,
    LogEvent.MQTT_RECONNECTING,
}

DETECTION_EVENTS = {
    LogEvent.DETECTION_PROCESSED,
    LogEvent.DETECTION_SERIALIZED,
    LogEvent.DETECTION_RECEIVED,
}

ZONE_EVENTS = {
    LogEvent.ZONE_TRIGGERED,
    LogEvent.ZONE_STATS_UPDATED,
    LogEvent.ZONE_EVENT_SERIALIZED,
    LogEvent.ZONE_EVENT_RECEIVED,
}

ERROR_EVENTS = {
    LogEvent.SERIALIZATION_ERROR,
    LogEvent.DESERIALIZATION_ERROR,
    LogEvent.SCHEMA_VALIDATION_ERROR,
    LogEvent.MQTT_CONNECTION_ERROR,
    LogEvent.MQTT_PUBLISH_ERROR,
}
