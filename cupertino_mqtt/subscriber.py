"""
MQTT Subscriber
==============

Bounded Context: Message Consumption

This module provides the subscriber for receiving detection and zone event messages
from MQTT broker.

Design:
- Thread-safe message consumption
- Callback-based architecture (async message handling)
- Automatic deserialization with error handling
- Reconnection support

Architecture:
    MQTT Broker → Subscriber → Callbacks → Visualizer

Message Flow:
    1. Subscriber receives JSON from MQTT
    2. Deserializes to typed schemas (DetectionMessage, ZoneEventMessage)
    3. Invokes user callback with typed message
    4. Continues listening (non-blocking)

Example (Visualizer):
    >>> from cupertino_mqtt import MessageSubscriber, create_logger
    >>> from cupertino_mqtt.schemas import DetectionMessage, ZoneEventMessage
    >>>
    >>> logger = create_logger("visualizer")
    >>>
    >>> def on_detection(msg: DetectionMessage):
    ...     print(f"Received {msg.detection_count} detections")
    ...     for det in msg.detections:
    ...         print(f"  - {det.class_name} at {det.bbox.center_x}, {det.bbox.center_y}")
    >>>
    >>> def on_zone_event(msg: ZoneEventMessage):
    ...     print(f"Received {msg.zone_count} zone events")
    ...     for zone in msg.zones:
    ...         print(f"  - Zone {zone.zone_id}: {zone.event_type.value}")
    >>>
    >>> subscriber = MessageSubscriber(
    ...     broker_host="localhost",
    ...     detection_topic="cupertino/detections",
    ...     zone_event_topic="cupertino/zone_events",
    ...     on_detection=on_detection,
    ...     on_zone_event=on_zone_event,
    ...     logger=logger
    ... )
    >>>
    >>> subscriber.connect()
    >>> subscriber.start()  # Non-blocking, callbacks run in background
    >>> # ... visualizer main loop ...
    >>> subscriber.stop()
"""

import json
import threading
from typing import Optional, Callable
import paho.mqtt.client as mqtt

from .schemas import DetectionMessage, ZoneEventMessage
from .logging import StructuredLogger, LogEvent


class MessageSubscriber:
    """
    MQTT subscriber for detection and zone event messages.

    Receives messages from broker, deserializes to typed schemas, and invokes
    user callbacks.

    Attributes:
        broker_host: MQTT broker hostname
        broker_port: MQTT broker port
        detection_topic: Topic for detection messages
        zone_event_topic: Topic for zone event messages
        client_id: MQTT client identifier
        logger: Structured logger instance
        on_detection: Callback for detection messages
        on_zone_event: Callback for zone event messages

    Thread Safety:
        Thread-safe via paho-mqtt's loop_start() and threading.Event

    Example:
        >>> subscriber = MessageSubscriber(
        ...     broker_host="localhost",
        ...     detection_topic="cupertino/detections",
        ...     zone_event_topic="cupertino/zone_events",
        ...     on_detection=detection_callback,
        ...     on_zone_event=zone_callback,
        ...     logger=logger
        ... )
        >>> subscriber.connect()
        >>> subscriber.start()
    """

    def __init__(
        self,
        broker_host: str,
        detection_topic: str,
        zone_event_topic: str,
        on_detection: Callable[[DetectionMessage], None],
        on_zone_event: Callable[[ZoneEventMessage], None],
        logger: StructuredLogger,
        broker_port: int = 1883,
        client_id: str = "cupertino_subscriber",
        username: Optional[str] = None,
        password: Optional[str] = None,
        qos: int = 0
    ):
        """
        Initialize MQTT subscriber.

        Args:
            broker_host: MQTT broker hostname
            detection_topic: Topic to subscribe for detections
            zone_event_topic: Topic to subscribe for zone events
            on_detection: Callback function for detection messages
            on_zone_event: Callback function for zone event messages
            logger: Structured logger instance
            broker_port: MQTT broker port (default: 1883)
            client_id: MQTT client ID (default: cupertino_subscriber)
            username: MQTT auth username (optional)
            password: MQTT auth password (optional)
            qos: Quality of Service (default: 0)

        Design Note:
            Callbacks are invoked in MQTT thread. Keep them fast or dispatch
            to worker threads if processing is heavy.
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.detection_topic = detection_topic
        self.zone_event_topic = zone_event_topic
        self.client_id = client_id
        self.logger = logger
        self.qos = qos

        # User callbacks
        self.on_detection = on_detection
        self.on_zone_event = on_zone_event

        # MQTT client setup
        self.client = mqtt.Client(client_id=client_id)
        if username and password:
            self.client.username_pw_set(username, password)

        # Callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # State
        self._connected = threading.Event()
        self._running = False
        self._stats_lock = threading.Lock()
        self._message_count = {'detections': 0, 'zone_events': 0}

    def _on_connect(
        self,
        client: mqtt.Client,
        userdata: any,
        flags: dict,
        rc: int
    ) -> None:
        """
        Callback when connection established.

        Automatically subscribes to configured topics.

        Args:
            client: MQTT client instance
            userdata: User data (unused)
            flags: Connection flags
            rc: Return code (0 = success)
        """
        if rc == 0:
            self._connected.set()

            # Subscribe to both topics
            client.subscribe(self.detection_topic, qos=self.qos)
            client.subscribe(self.zone_event_topic, qos=self.qos)

            self.logger.info(
                event=LogEvent.MQTT_CONNECTED,
                message="Connected to MQTT broker and subscribed to topics",
                metadata={
                    'broker': f"{self.broker_host}:{self.broker_port}",
                    'detection_topic': self.detection_topic,
                    'zone_event_topic': self.zone_event_topic
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
        userdata: any,
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

    def _on_message(
        self,
        client: mqtt.Client,
        userdata: any,
        msg: mqtt.MQTTMessage
    ) -> None:
        """
        Callback when message received.

        Deserializes JSON and invokes appropriate user callback.

        Args:
            client: MQTT client instance
            userdata: User data (unused)
            msg: MQTT message with topic and payload
        """
        try:
            # Decode JSON
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)

            # Route by topic
            if msg.topic == self.detection_topic:
                self._handle_detection_message(data)
            elif msg.topic == self.zone_event_topic:
                self._handle_zone_event_message(data)
            else:
                self.logger.warning(
                    event=LogEvent.DESERIALIZATION_ERROR,
                    message=f"Received message from unknown topic: {msg.topic}"
                )

        except json.JSONDecodeError as e:
            self.logger.error(
                event=LogEvent.DESERIALIZATION_ERROR,
                message="Failed to decode JSON message",
                exc_info=e,
                metadata={'topic': msg.topic}
            )
        except Exception as e:
            self.logger.error(
                event=LogEvent.DESERIALIZATION_ERROR,
                message="Error processing message",
                exc_info=e,
                metadata={'topic': msg.topic}
            )

    def _handle_detection_message(self, data: dict) -> None:
        """
        Handle detection message.

        Deserializes to DetectionMessage and invokes user callback.

        Args:
            data: JSON data dictionary
        """
        try:
            # Deserialize
            detection_msg = DetectionMessage.from_dict(data)

            # Update stats
            with self._stats_lock:
                self._message_count['detections'] += 1

            # Log
            self.logger.info(
                event=LogEvent.DETECTION_RECEIVED,
                message=f"Received detection message",
                metadata={
                    'frame_id': detection_msg.frame_id,
                    'detection_count': detection_msg.detection_count,
                    'source_id': detection_msg.source_id
                }
            )

            # Invoke user callback
            self.on_detection(detection_msg)

        except ValueError as e:
            self.logger.error(
                event=LogEvent.SCHEMA_VALIDATION_ERROR,
                message="Detection message failed schema validation",
                exc_info=e,
                metadata={'data': data}
            )
        except Exception as e:
            self.logger.error(
                event=LogEvent.DESERIALIZATION_ERROR,
                message="Error handling detection message",
                exc_info=e
            )

    def _handle_zone_event_message(self, data: dict) -> None:
        """
        Handle zone event message.

        Deserializes to ZoneEventMessage and invokes user callback.

        Args:
            data: JSON data dictionary
        """
        try:
            # Deserialize
            zone_event_msg = ZoneEventMessage.from_dict(data)

            # Update stats
            with self._stats_lock:
                self._message_count['zone_events'] += 1

            # Log
            self.logger.info(
                event=LogEvent.ZONE_EVENT_RECEIVED,
                message=f"Received zone event message",
                metadata={
                    'frame_id': zone_event_msg.frame_id,
                    'zone_count': zone_event_msg.zone_count,
                    'source_id': zone_event_msg.source_id,
                    'zone_ids': [z.zone_id for z in zone_event_msg.zones]
                }
            )

            # Invoke user callback
            self.on_zone_event(zone_event_msg)

        except ValueError as e:
            self.logger.error(
                event=LogEvent.SCHEMA_VALIDATION_ERROR,
                message="Zone event message failed schema validation",
                exc_info=e,
                metadata={'data': data}
            )
        except Exception as e:
            self.logger.error(
                event=LogEvent.DESERIALIZATION_ERROR,
                message="Error handling zone event message",
                exc_info=e
            )

    def connect(self, timeout: float = 10.0) -> bool:
        """
        Connect to MQTT broker.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connected successfully, False otherwise

        Example:
            >>> if subscriber.connect():
            ...     subscriber.start()
        """
        try:
            self.client.connect(self.broker_host, self.broker_port)

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

    def start(self) -> None:
        """
        Start subscriber loop in background thread.

        Non-blocking. Messages will be received and callbacks invoked
        in background MQTT thread.

        Example:
            >>> subscriber.connect()
            >>> subscriber.start()
            >>> # Main loop continues here
            >>> while True:
            ...     # Visualizer rendering
            ...     pass
        """
        if not self._connected.is_set():
            self.logger.warning(
                event=LogEvent.MQTT_CONNECTION_ERROR,
                message="Cannot start: not connected to broker"
            )
            return

        self._running = True
        self.client.loop_start()

        self.logger.info(
            event=LogEvent.MQTT_CONNECTED,
            message="Subscriber started (listening for messages)",
            metadata={
                'detection_topic': self.detection_topic,
                'zone_event_topic': self.zone_event_topic
            }
        )

    def stop(self) -> None:
        """
        Stop subscriber loop and disconnect.

        Blocks until network loop stops (should be fast).

        Example:
            >>> subscriber.stop()
        """
        self._running = False
        self.client.loop_stop()
        self.client.disconnect()

        stats = self.get_stats()
        self.logger.info(
            event=LogEvent.MQTT_DISCONNECTED,
            message="Subscriber stopped",
            metadata=stats
        )

    def is_connected(self) -> bool:
        """Check if currently connected to broker."""
        return self._connected.is_set()

    def is_running(self) -> bool:
        """Check if subscriber is running (listening)."""
        return self._running

    def get_stats(self) -> dict:
        """
        Get subscriber statistics.

        Returns:
            Dictionary with message counts and connection status

        Example:
            >>> stats = subscriber.get_stats()
            >>> print(f"Received {stats['detections_received']} detections")
        """
        with self._stats_lock:
            return {
                'detections_received': self._message_count['detections'],
                'zone_events_received': self._message_count['zone_events'],
                'connected': self._connected.is_set(),
                'running': self._running,
                'detection_topic': self.detection_topic,
                'zone_event_topic': self.zone_event_topic,
                'broker': f"{self.broker_host}:{self.broker_port}"
            }
