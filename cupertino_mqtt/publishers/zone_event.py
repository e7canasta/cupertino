"""
Zone Event Publisher
===================

Bounded Context: Zone Event Message Production

This module provides the publisher for zone monitoring event messages.

Design:
- Inherits from BasePublisher (connection management)
- Formats ZoneEventMessage to JSON
- Publishes to configured topic
- Logs structured events

Message Flow:
    ZoneMonitor → ZoneEventMessage → ZoneEventPublisher → MQTT Broker

Example:
    >>> from cupertino_mqtt.publishers import ZoneEventPublisher
    >>> from cupertino_mqtt.schemas import (
    ...     ZoneEvent, ZoneEventMessage, ZoneType, EventType,
    ...     ZoneStats, Timestamp
    ... )
    >>> from cupertino_mqtt.logging import create_logger
    >>>
    >>> logger = create_logger("processor")
    >>> publisher = ZoneEventPublisher(
    ...     broker_host="localhost",
    ...     topic="cupertino/zone_events",
    ...     logger=logger
    ... )
    >>>
    >>> # Connect
    >>> publisher.connect()
    >>>
    >>> # Create zone event message
    >>> zone_event = ZoneEvent(
    ...     zone_id="entrance",
    ...     zone_type=ZoneType.POLYGON,
    ...     event_type=EventType.INSIDE,
    ...     stats=ZoneStats(current_count=2),
    ...     triggered_by=[1, 3]
    ... )
    >>> msg = ZoneEventMessage(
    ...     schema_version="1.0",
    ...     timestamp=Timestamp.now(),
    ...     frame_id=123,
    ...     source_id=0,
    ...     zones=[zone_event]
    ... )
    >>>
    >>> # Publish
    >>> publisher.publish_zone_event(msg)
"""

from typing import Dict, Any, Optional
from .base import BasePublisher
from ..schemas import ZoneEventMessage
from ..logging import StructuredLogger, LogEvent


class ZoneEventPublisher(BasePublisher):
    """
    Publisher for zone monitoring event messages.

    Handles formatting and publishing of ZoneEventMessage instances to MQTT.

    Attributes:
        Same as BasePublisher, plus:
        schema_version: Current schema version for messages

    Example:
        >>> publisher = ZoneEventPublisher(
        ...     broker_host="localhost",
        ...     broker_port=1883,
        ...     topic="cupertino/zone_events",
        ...     client_id="processor_zones",
        ...     logger=logger
        ... )
    """

    def __init__(
        self,
        broker_host: str,
        topic: str,
        logger: StructuredLogger,
        broker_port: int = 1883,
        client_id: str = "cupertino_zone_publisher",
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 0
    ):
        """
        Initialize zone event publisher.

        Args:
            broker_host: MQTT broker hostname
            topic: Topic to publish zone event messages
            logger: Structured logger instance
            broker_port: MQTT broker port (default: 1883)
            client_id: MQTT client ID (default: cupertino_zone_publisher)
            username: MQTT auth username (optional)
            password: MQTT auth password (optional)
            qos: Quality of Service (default: 0)
        """
        super().__init__(
            broker_host=broker_host,
            broker_port=broker_port,
            topic=topic,
            client_id=client_id,
            logger=logger,
            username=username,
            password=password,
            qos=qos
        )
        self.schema_version = "1.0"

    def format_message(self, zone_event_msg: ZoneEventMessage) -> Dict[str, Any]:
        """
        Format ZoneEventMessage to JSON-compatible dict.

        Args:
            zone_event_msg: ZoneEventMessage instance

        Returns:
            Dictionary ready for JSON serialization

        Raises:
            ValueError: If zone_event_msg is invalid

        Example:
            >>> msg = ZoneEventMessage(...)
            >>> formatted = publisher.format_message(msg)
            >>> # formatted is JSON-serializable dict
        """
        try:
            formatted = zone_event_msg.to_dict()

            self.logger.info(
                event=LogEvent.ZONE_EVENT_SERIALIZED,
                message=f"Serialized zone event message",
                metadata={
                    'frame_id': zone_event_msg.frame_id,
                    'zone_count': zone_event_msg.zone_count,
                    'source_id': zone_event_msg.source_id
                }
            )

            return formatted

        except Exception as e:
            self.logger.error(
                event=LogEvent.SERIALIZATION_ERROR,
                message="Failed to serialize zone event message",
                exc_info=e,
                metadata={'frame_id': getattr(zone_event_msg, 'frame_id', None)}
            )
            raise ValueError(f"Failed to format zone event message: {e}")

    def publish_zone_event(self, zone_event_msg: ZoneEventMessage) -> bool:
        """
        Publish zone event message to MQTT broker.

        This is the main public API for publishing zone events.

        Args:
            zone_event_msg: ZoneEventMessage instance

        Returns:
            True if published successfully, False otherwise

        Example:
            >>> msg = ZoneEventMessage(
            ...     schema_version="1.0",
            ...     timestamp=Timestamp.now(),
            ...     frame_id=123,
            ...     source_id=0,
            ...     zones=[zone1, zone2]
            ... )
            >>> success = publisher.publish_zone_event(msg)
        """
        try:
            # Format message
            message_data = self.format_message(zone_event_msg)

            # Publish via base class
            success = self.publish(message_data)

            if success:
                # Extract zone IDs for logging
                zone_ids = [zone.zone_id for zone in zone_event_msg.zones]

                self.logger.info(
                    event=LogEvent.ZONE_TRIGGERED,
                    message=f"Published {zone_event_msg.zone_count} zone events",
                    metadata={
                        'frame_id': zone_event_msg.frame_id,
                        'zone_count': zone_event_msg.zone_count,
                        'zone_ids': zone_ids
                    }
                )

            return success

        except Exception as e:
            self.logger.error(
                event=LogEvent.MQTT_PUBLISH_ERROR,
                message="Error publishing zone event message",
                exc_info=e,
                metadata={
                    'frame_id': zone_event_msg.frame_id,
                    'topic': self.topic
                }
            )
            return False
