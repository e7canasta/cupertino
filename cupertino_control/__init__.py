"""
cupertino_control - Control Plane for StreamProcessor

Bounded Context: MQTT-based command-and-control
Responsibilities:
  - MQTT connection management (Control Plane)
  - Command registration and validation
  - Command execution delegation

Architecture:
  - CommandRegistry: Explicit registration pattern (like Adeline)
  - MQTTControlPlane: MQTT client + command reception
  - QoS 1 for control commands (at-least-once delivery)

Design Philosophy:
  - Explicit registration (fail-fast, no runtime surprises)
  - Conditional command registration (based on capabilities)
  - Thread-safe (registry uses locks)
  - Clear error messages (lists available commands on error)

References:
  - Adeline control/plane.py
  - Adeline control/registry.py
"""

from .registry import CommandRegistry, CommandNotAvailableError
from .plane import MQTTControlPlane

__all__ = [
    "CommandRegistry",
    "CommandNotAvailableError",
    "MQTTControlPlane",
]
