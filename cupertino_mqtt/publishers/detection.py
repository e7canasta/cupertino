"""
Detection Publisher
==================

Bounded Context: Detection Message Production

This module provides the publisher for YOLO detection messages.

Design:
- Inherits from BasePublisher (connection management)
- Formats DetectionMessage to JSON
- Publishes to configured topic
- Logs structured events

Message Flow:
    YOLO Inference → DetectionMessage → DetectionPublisher → MQTT Broker

Example:
    >>> from cupertino_mqtt.publishers import DetectionPublisher
    >>> from cupertino_mqtt.schemas import Detection, DetectionMessage, BBox, Timestamp
    >>> from cupertino_mqtt.logging import create_logger
    >>>
    >>> logger = create_logger("processor")
    >>> publisher = DetectionPublisher(
    ...     broker_host="localhost",
    ...     topic="cupertino/detections",
    ...     logger=logger
    ... )
    >>>
    >>> # Connect
    >>> publisher.connect()
    >>>
    >>> # Create detection message
    >>> det = Detection(
    ...     tracker_id=1,
    ...     class_name="person",
    ...     confidence=0.95,
    ...     bbox=BBox(x=100, y=200, width=50, height=100)
    ... )
    >>> msg = DetectionMessage(
    ...     schema_version="1.0",
    ...     timestamp=Timestamp.now(),
    ...     frame_id=123,
    ...     source_id=0,
    ...     detections=[det]
    ... )
    >>>
    >>> # Publish
    >>> publisher.publish_detection(msg)
"""

from typing import Dict, Any, Optional
from .base import BasePublisher
from ..schemas import DetectionMessage
from ..logging import StructuredLogger, LogEvent


class DetectionPublisher(BasePublisher):
    """
    Publisher for YOLO detection messages.

    Handles formatting and publishing of DetectionMessage instances to MQTT.

    Attributes:
        Same as BasePublisher, plus:
        schema_version: Current schema version for messages

    Example:
        >>> publisher = DetectionPublisher(
        ...     broker_host="localhost",
        ...     broker_port=1883,
        ...     topic="cupertino/detections",
        ...     client_id="processor_detections",
        ...     logger=logger
        ... )
    """

    def __init__(
        self,
        broker_host: str,
        topic: str,
        logger: StructuredLogger,
        broker_port: int = 1883,
        client_id: str = "cupertino_detection_publisher",
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 0
    ):
        """
        Initialize detection publisher.

        Args:
            broker_host: MQTT broker hostname
            topic: Topic to publish detection messages
            logger: Structured logger instance
            broker_port: MQTT broker port (default: 1883)
            client_id: MQTT client ID (default: cupertino_detection_publisher)
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

    def format_message(self, detection_msg: DetectionMessage) -> Dict[str, Any]:
        """
        Format DetectionMessage to JSON-compatible dict.

        Args:
            detection_msg: DetectionMessage instance

        Returns:
            Dictionary ready for JSON serialization

        Raises:
            ValueError: If detection_msg is invalid

        Example:
            >>> msg = DetectionMessage(...)
            >>> formatted = publisher.format_message(msg)
            >>> # formatted is JSON-serializable dict
        """
        try:
            formatted = detection_msg.to_dict()

            self.logger.info(
                event=LogEvent.DETECTION_SERIALIZED,
                message=f"Serialized detection message",
                metadata={
                    'frame_id': detection_msg.frame_id,
                    'detection_count': detection_msg.detection_count,
                    'source_id': detection_msg.source_id
                }
            )

            return formatted

        except Exception as e:
            self.logger.error(
                event=LogEvent.SERIALIZATION_ERROR,
                message="Failed to serialize detection message",
                exc_info=e,
                metadata={'frame_id': getattr(detection_msg, 'frame_id', None)}
            )
            raise ValueError(f"Failed to format detection message: {e}")

    def publish_detection(self, detection_msg: DetectionMessage) -> bool:
        """
        Publish detection message to MQTT broker.

        This is the main public API for publishing detections.

        Args:
            detection_msg: DetectionMessage instance

        Returns:
            True if published successfully, False otherwise

        Example:
            >>> msg = DetectionMessage(
            ...     schema_version="1.0",
            ...     timestamp=Timestamp.now(),
            ...     frame_id=123,
            ...     source_id=0,
            ...     detections=[det1, det2]
            ... )
            >>> success = publisher.publish_detection(msg)
        """
        try:
            # Format message
            message_data = self.format_message(detection_msg)

            # Publish via base class
            success = self.publish(message_data)

            if success:
                self.logger.info(
                    event=LogEvent.DETECTION_PROCESSED,
                    message=f"Published {detection_msg.detection_count} detections",
                    metadata={
                        'frame_id': detection_msg.frame_id,
                        'detection_count': detection_msg.detection_count,
                        'tracker_ids': detection_msg.get_tracker_ids()
                    }
                )

            return success

        except Exception as e:
            self.logger.error(
                event=LogEvent.MQTT_PUBLISH_ERROR,
                message="Error publishing detection message",
                exc_info=e,
                metadata={
                    'frame_id': detection_msg.frame_id,
                    'topic': self.topic
                }
            )
            return False
