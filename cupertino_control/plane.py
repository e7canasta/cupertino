"""
MQTTControlPlane - MQTT Control Plane for StreamProcessor

Bounded Context: MQTT connection management + command reception
Responsibilities:
  - MQTT connection lifecycle (connect, disconnect)
  - Command message reception (subscribe to command topic)
  - Status publishing (publish to status topic)
  - Command delegation to CommandRegistry

QoS Policy:
  - Commands: QoS 1 (at-least-once delivery)
  - Status: QoS 1 + retained (last status persisted)

Threading:
  - MQTT client runs own background thread (loop_start/loop_stop)
  - Callbacks (_on_connect, _on_message) run in MQTT thread
  - Command handlers run in MQTT thread (keep them fast!)

Inspiration: Adeline control/plane.py
"""

import json
import logging
from datetime import datetime
from threading import Event
from typing import Optional

import paho.mqtt.client as mqtt

from .registry import CommandRegistry, CommandNotAvailableError

logger = logging.getLogger(__name__)


class MQTTControlPlane:
    """
    MQTT Control Plane for receiving commands and publishing status.

    Features:
      - QoS 1 for reliable command delivery
      - Retained status messages (last status persisted)
      - Event-based connection synchronization
      - CommandRegistry pattern for command execution

    Threading:
      - MQTT client runs in background thread (via loop_start)
      - Callbacks run in MQTT thread (keep handlers fast!)

    Example:
        control_plane = MQTTControlPlane(
            broker_host="localhost",
            broker_port=1883,
            command_topic="cupertino/control/commands",
            status_topic="cupertino/control/status",
            client_id="stream_processor_01"
        )

        # Register commands
        control_plane.command_registry.register('pause', handler.pause, "Pause processing")

        # Connect
        if control_plane.connect(timeout=5.0):
            print("Connected to MQTT broker")

        # Later: disconnect
        control_plane.disconnect()
    """

    def __init__(
        self,
        broker_host: str,
        broker_port: int,
        command_topic: str,
        status_topic: str,
        client_id: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Initialize MQTT Control Plane.

        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port (typically 1883)
            command_topic: Topic for receiving commands (subscribe)
            status_topic: Topic for publishing status (publish)
            client_id: MQTT client identifier
            username: Optional MQTT authentication username
            password: Optional MQTT authentication password
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.command_topic = command_topic
        self.status_topic = status_topic
        self.client_id = client_id

        # MQTT client
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv311)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Authentication
        if username and password:
            self.client.username_pw_set(username, password)

        # Connection synchronization
        self._connected = Event()
        self._running = False

        # Command registry
        self.command_registry = CommandRegistry()

    def connect(self, timeout: float = 5.0) -> bool:
        """
        Connect to MQTT broker with timeout.

        Args:
            timeout: Connection timeout in seconds

        Returns:
            True if connected successfully, False otherwise

        Thread Safety: Blocks until connected or timeout
        """
        try:
            logger.info(f"🔌 Connecting to MQTT broker: {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
            self._running = True

            # Wait for connection with timeout
            if self._connected.wait(timeout=timeout):
                logger.info("✅ MQTT Control Plane connected")
                return True
            else:
                logger.error(f"❌ Connection timeout after {timeout}s")
                return False

        except Exception as e:
            logger.error(f"❌ Error connecting to MQTT: {e}")
            return False

    def disconnect(self) -> None:
        """
        Disconnect from MQTT broker.

        Thread Safety: Safe to call multiple times
        """
        if self._running:
            logger.info("🔌 Disconnecting from MQTT broker")
            self.publish_status("disconnected")
            self.client.loop_stop()
            self.client.disconnect()
            self._running = False
            self._connected.clear()
            logger.info("✅ MQTT Control Plane disconnected")

    def publish_status(self, status: str) -> None:
        """
        Publish status update to status topic.

        Args:
            status: Status string (e.g., "running", "paused", "stopped")

        QoS: 1 (at-least-once)
        Retained: True (last status persisted)

        Thread Safety: Safe to call from any thread
        """
        message = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "client_id": self.client_id,
        }

        try:
            self.client.publish(
                self.status_topic,
                json.dumps(message),
                qos=1,
                retain=True,  # Last status retained for new subscribers
            )
            logger.debug(f"📤 Status published: {status}")
        except Exception as e:
            logger.error(f"❌ Error publishing status: {e}")

    # ===== MQTT Callbacks (run in MQTT thread) =====

    def _on_connect(self, client, userdata, flags, rc):
        """
        MQTT callback: connection established.

        Thread: Runs in MQTT client thread
        """
        if rc == 0:
            logger.info(f"✅ Connected to broker (rc={rc})")

            # Subscribe to command topic with QoS 1
            client.subscribe(self.command_topic, qos=1)
            logger.info(f"📥 Subscribed to: {self.command_topic} (QoS 1)")

            # Publish connected status
            self.publish_status("connected")

            # Signal connection event
            self._connected.set()
        else:
            logger.error(f"❌ Connection failed (rc={rc})")
            self._connected.clear()

    def _on_disconnect(self, client, userdata, rc):
        """
        MQTT callback: disconnection detected.

        Thread: Runs in MQTT client thread
        """
        if rc != 0:
            logger.warning(f"⚠️ Unexpected disconnection (rc={rc})")
        else:
            logger.info("✅ Disconnected from broker")
        self._connected.clear()

    def _on_message(self, client, userdata, msg):
        """
        MQTT callback: command message received.

        Thread: Runs in MQTT client thread
        Keep this fast! Long-running operations should be delegated.
        """
        try:
            # Decode payload
            payload = msg.payload.decode('utf-8')
            logger.debug(f"📦 Command received: {payload}")

            # Parse JSON
            command_data = json.loads(payload)
            command = command_data.get('command', '').lower()

            if not command:
                logger.warning("⚠️ Empty command received")
                return

            logger.info(f"🎯 Executing command: {command}")

            # Execute via registry (pass full command_data)
            try:
                self.command_registry.execute(command, command_data)
                logger.debug(f"✅ Command '{command}' executed successfully")

            except CommandNotAvailableError as e:
                logger.warning(f"⚠️ {e}")
                # List available commands to help user
                available = ', '.join(sorted(self.command_registry.available_commands))
                logger.info(f"💡 Available commands: {available}")

        except json.JSONDecodeError as e:
            logger.error(f"❌ Error decoding JSON: {msg.payload} ({e})")
        except Exception as e:
            logger.error(f"❌ Error processing message: {e}", exc_info=True)
