"""
Base MQTT Publisher
==================

Bounded Context: MQTT Infrastructure

This module provides the abstract base class for MQTT publishers.

Design:
- Connection management (connect, disconnect, reconnect)
- QoS 0 (fire-and-forget) for high throughput
- Thread-safe (paho-mqtt loop)
- Structured logging integration

Architecture:
    BasePublisher (abstract)
        ↓
    DetectionPublisher, ZoneEventPublisher (concrete)

Responsibilities:
- MQTT connection lifecycle
- Message publishing to broker
- Error handling and logging
- NOT responsible for: Message formatting (delegated to subclasses)

Example:
    >>> class MyPublisher(BasePublisher):
    ...     def format_message(self, data):
    ...         return {"my_data": data}
"""

import json
import threading
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import paho.mqtt.client as mqtt

from ..logging import StructuredLogger, LogEvent


class BasePublisher(ABC):
    """
    Abstract base class for MQTT publishers.

    Handles MQTT connection management and message publication.
    Subclasses must implement format_message() for message-specific logic.

    Attributes:
        broker_host: MQTT broker hostname
        broker_port: MQTT broker port
        topic: MQTT topic to publish to
        client_id: MQTT client identifier
        qos: Quality of Service (default: 0 for high throughput)
        logger: Structured logger instance

    Thread Safety:
        Thread-safe via paho-mqtt's loop_start() and threading.Event
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        topic: str,
        client_id: str,
        logger: StructuredLogger,
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 0
    ):
        """
        Initialize MQTT publisher.

        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            topic: Topic to publish to
            client_id: Unique client identifier
            logger: Structured logger for observability
            username: MQTT authentication username (optional)
            password: MQTT authentication password (optional)
            qos: Quality of Service (0=fire-and-forget, 1=at-least-once)

        Design Note:
            QoS 0 is default for high-throughput scenarios (25 FPS).
            Use QoS 1 only for critical control messages.
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic = topic
        self.client_id = client_id
        self.logger = logger
        self.qos = qos

        # MQTT client setup
        self.client = mqtt.Client(client_id=client_id)
        if username and password:
            self.client.username_pw_set(username, password)

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect

        # Connection state
        self._connected = threading.Event()
        self._message_count = 0
        self._stats_lock = threading.Lock()

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: Any,
        flags: Dict[str, Any],
        rc: int
    ) -> None:
        """
        Callback when connection established.

        Args:
            client: MQTT client instance
            userdata: User data (unused)
            flags: Connection flags
            rc: Return code (0 = success)
        """
        if rc == 0:
            self._connected.set()
            self.logger.info(
                event=LogEvent.MQTT_CONNECTED,
                message=f"Connected to MQTT broker",
                metadata={
                    'broker': f"{self.broker_host}:{self.broker_port}",
                    'client_id': self.client_id,
                    'topic': self.topic
                }
            )
        else:
            self.logger.error(
                event=LogEvent.MQTT_CONNECTION_ERROR,
                message=f"Failed to connect to broker (rc={rc})",
                metadata={'broker': f"{self.broker_host}:{self.broker_port}"}
            )

    def _on_disconnect(
        self,
        client: mqtt.Client,
        userdata: Any,
        rc: int
    ) -> None:
        """
        Callback when disconnected from broker.

        Args:
            client: MQTT client instance
            userdata: User data (unused)
            rc: Disconnect reason code
        """
        self._connected.clear()
        self.logger.warning(
            event=LogEvent.MQTT_DISCONNECTED,
            message="Disconnected from MQTT broker",
            metadata={
                'broker': f"{self.broker_host}:{self.broker_port}",
                'reason_code': rc
            }
        )

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to MQTT broker.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connected successfully, False otherwise

        Example:
            >>> publisher = DetectionPublisher(...)
            >>> if publisher.connect():
            ...     publisher.publish(message)
        """
        try:
            self.client.connect(self.broker_host, self.broker_port)
            self.client.loop_start()

            # Wait for connection with timeout
            if self._connected.wait(timeout=timeout):
                return True
            else:
                self.logger.error(
                    event=LogEvent.MQTT_CONNECTION_ERROR,
                    message="Connection timeout",
                    metadata={'timeout': timeout}
                )
                return False

        except Exception as e:
            self.logger.error(
                event=LogEvent.MQTT_CONNECTION_ERROR,
                message="Failed to connect to broker",
                exc_info=e,
                metadata={'broker': f"{self.broker_host}:{self.broker_port}"}
            )
            return False

    def disconnect(self) -> None:
        """
        Disconnect from MQTT broker gracefully.

        Stops the network loop and disconnects the client.
        """
        try:
            self.client.loop_stop()
            self.client.disconnect()
            self.logger.info(
                event=LogEvent.MQTT_DISCONNECTED,
                message="Disconnected from broker",
                metadata={'message_count': self._message_count}
            )
        except Exception as e:
            self.logger.error(
                event=LogEvent.MQTT_CONNECTION_ERROR,
                message="Error during disconnect",
                exc_info=e
            )

    def is_connected(self) -> bool:
        """Check if currently connected to broker."""
        return self._connected.is_set()

    @abstractmethod
    def format_message(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Format message for publication.

        Subclasses must implement this to provide message-specific formatting.

        Returns:
            Dictionary ready for JSON serialization

        Example (in subclass):
            >>> def format_message(self, detection_msg: DetectionMessage):
            ...     return detection_msg.to_dict()
        """
        raise NotImplementedError("Subclasses must implement format_message()")

    def publish(
        self,
        message_data: Dict[str, Any],
        retain: bool = False
    ) -> bool:
        """
        Publish message to MQTT broker.

        Args:
            message_data: Message dictionary (already formatted)
            retain: MQTT retain flag (default: False)

        Returns:
            True if published successfully, False otherwise

        Design Note:
            This method accepts pre-formatted dictionaries. Subclasses
            should call format_message() before calling publish().
        """
        if not self._connected.is_set():
            self.logger.warning(
                event=LogEvent.MQTT_PUBLISH_FAILED,
                message="Cannot publish: not connected to broker"
            )
            return False

        try:
            # Serialize to JSON
            json_message = json.dumps(message_data)

            # Publish
            result = self.client.publish(
                topic=self.topic,
                payload=json_message,
                qos=self.qos,
                retain=retain
            )

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                with self._stats_lock:
                    self._message_count += 1

                self.logger.info(
                    event=LogEvent.MQTT_PUBLISH_SUCCESS,
                    message="Published message",
                    metadata={
                        'topic': self.topic,
                        'message_count': self._message_count,
                        'qos': self.qos
                    }
                )
                return True
            else:
                self.logger.warning(
                    event=LogEvent.MQTT_PUBLISH_FAILED,
                    message=f"Publish failed (rc={result.rc})",
                    metadata={'topic': self.topic}
                )
                return False

        except Exception as e:
            self.logger.error(
                event=LogEvent.MQTT_PUBLISH_ERROR,
                message="Error publishing message",
                exc_info=e,
                metadata={'topic': self.topic}
            )
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get publisher statistics.

        Returns:
            Dictionary with message count and connection status

        Example:
            >>> stats = publisher.get_stats()
            >>> print(f"Published {stats['message_count']} messages")
        """
        with self._stats_lock:
            return {
                'message_count': self._message_count,
                'connected': self._connected.is_set(),
                'topic': self.topic,
                'broker': f"{self.broker_host}:{self.broker_port}"
            }
