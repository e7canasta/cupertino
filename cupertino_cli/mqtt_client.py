"""
MQTT client wrapper for sending commands to StreamProcessor.

Handles MQTT connection, publishing, and disconnection.
"""

import json
import paho.mqtt.client as mqtt
from typing import Dict, Any, Optional


class MQTTCommandClient:
    """
    MQTT client for sending commands to StreamProcessor.

    Publishes commands to the control plane topic with QoS 1.
    """

    def __init__(
        self,
        broker: str = "localhost",
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize MQTT command client.

        Args:
            broker: MQTT broker host
            port: MQTT broker port
            username: Optional MQTT username
            password: Optional MQTT password
        """
        self.broker = broker
        self.port = port
        self.username = username
        self.password = password

        self.client = mqtt.Client()

        if username and password:
            self.client.username_pw_set(username, password)

    def send_command(
        self,
        topic: str,
        command: Dict[str, Any],
        qos: int = 1
    ) -> None:
        """
        Send command to MQTT topic.

        Args:
            topic: MQTT topic (e.g., "cupertino/control/cam_01/commands")
            command: Command dictionary (will be JSON serialized)
            qos: Quality of Service (default: 1 for control commands)

        Raises:
            ConnectionError: If unable to connect to MQTT broker
            ValueError: If command serialization fails
        """
        try:
            # Connect to broker
            self.client.connect(self.broker, self.port, keepalive=60)

            # Serialize command to JSON
            payload = json.dumps(command)

            # Publish command
            result = self.client.publish(topic, payload, qos=qos)
            result.wait_for_publish()

            # Disconnect
            self.client.disconnect()

            print(f"✅ Command sent: {command.get('command', 'unknown')}")

        except ConnectionRefusedError:
            raise ConnectionError(
                f"Unable to connect to MQTT broker at {self.broker}:{self.port}. "
                "Is mosquitto running?"
            )
        except json.JSONEncodeError as e:
            raise ValueError(f"Invalid command data: {e}")
        except Exception as e:
            raise RuntimeError(f"Failed to send command: {e}")
