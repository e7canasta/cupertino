"""
Structured JSON Logger
=====================

Bounded Context: Observability Infrastructure

This module provides a structured logger that outputs JSON logs for production systems.

Design:
- JSON output (compatible with log aggregators)
- Thread-safe (uses standard logging module)
- Contextual metadata (component, frame_id, etc.)
- Type-safe events (LogEvent enum)

Architecture:
- Wraps Python's logging module
- Adds structured metadata
- Formats as JSON for stdout/file

Example:
    >>> logger = StructuredLogger(component="processor")
    >>> logger.info(
    ...     event=LogEvent.DETECTION_PROCESSED,
    ...     message="Processed detections",
    ...     metadata={'frame_id': 123, 'count': 3}
    ... )

Output:
    {
        "timestamp": "2025-10-24T15:30:45.123456",
        "level": "INFO",
        "component": "processor",
        "event": "detection.processed",
        "message": "Processed detections",
        "metadata": {"frame_id": 123, "count": 3}
    }
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from .events import LogEvent


class StructuredLogger:
    """
    JSON structured logger for production observability.

    Wraps Python's logging module with structured metadata support.

    Attributes:
        component: Component name (e.g., "processor", "visualizer")
        logger: Underlying Python logger instance

    Example:
        >>> logger = StructuredLogger("processor")
        >>> logger.info(
        ...     event=LogEvent.MQTT_CONNECTED,
        ...     message="Connected to broker",
        ...     metadata={'broker': 'localhost:1883'}
        ... )

    Thread Safety:
        Thread-safe via Python's logging module.
    """

    def __init__(
        self,
        component: str,
        level: int = logging.INFO,
        logger_name: Optional[str] = None
    ):
        """
        Initialize structured logger.

        Args:
            component: Component identifier (e.g., "processor")
            level: Logging level (default: INFO)
            logger_name: Custom logger name (default: cupertino_mqtt.<component>)
        """
        self.component = component
        self.logger_name = logger_name or f"cupertino_mqtt.{component}"
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(level)

        # Configure JSON formatter if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)

    def _log(
        self,
        level: str,
        event: LogEvent,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ) -> None:
        """
        Internal log method with structured format.

        Args:
            level: Log level (INFO, WARNING, ERROR)
            event: Typed log event
            message: Human-readable message
            metadata: Additional context (frame_id, zone_id, etc.)
            exc_info: Exception for ERROR logs
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': level,
            'component': self.component,
            'event': event.value,
            'message': message,
        }

        if metadata:
            log_entry['metadata'] = metadata

        if exc_info:
            log_entry['exception'] = {
                'type': type(exc_info).__name__,
                'message': str(exc_info)
            }

        # Log as JSON string
        log_level = getattr(logging, level)
        self.logger.log(
            log_level,
            json.dumps(log_entry),
            exc_info=exc_info if level == 'ERROR' else None
        )

    def info(
        self,
        event: LogEvent,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log INFO level message.

        Args:
            event: Typed log event
            message: Human-readable message
            metadata: Additional context

        Example:
            >>> logger.info(
            ...     event=LogEvent.DETECTION_PROCESSED,
            ...     message="Processed 3 detections",
            ...     metadata={'frame_id': 123}
            ... )
        """
        self._log('INFO', event, message, metadata)

    def warning(
        self,
        event: LogEvent,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log WARNING level message.

        Args:
            event: Typed log event
            message: Human-readable message
            metadata: Additional context

        Example:
            >>> logger.warning(
            ...     event=LogEvent.MQTT_DISCONNECTED,
            ...     message="Lost connection to broker",
            ...     metadata={'broker': 'localhost:1883'}
            ... )
        """
        self._log('WARNING', event, message, metadata)

    def error(
        self,
        event: LogEvent,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        exc_info: Optional[Exception] = None
    ) -> None:
        """
        Log ERROR level message.

        Args:
            event: Typed log event
            message: Human-readable message
            metadata: Additional context
            exc_info: Exception instance for traceback

        Example:
            >>> try:
            ...     risky_operation()
            ... except ValueError as e:
            ...     logger.error(
            ...         event=LogEvent.SERIALIZATION_ERROR,
            ...         message="Failed to serialize detection",
            ...         exc_info=e,
            ...         metadata={'frame_id': 123}
            ...     )
        """
        self._log('ERROR', event, message, metadata, exc_info)

    def set_level(self, level: int) -> None:
        """
        Change logging level dynamically.

        Args:
            level: New logging level (logging.DEBUG, INFO, WARNING, ERROR)

        Example:
            >>> logger.set_level(logging.DEBUG)
        """
        self.logger.setLevel(level)


class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs as JSON.

    This formatter is used internally by StructuredLogger.
    It handles the final JSON serialization of log records.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.

        Args:
            record: Python logging record

        Returns:
            JSON-formatted log string
        """
        # The message from StructuredLogger is already JSON
        # Just pass it through
        return record.getMessage()


# Convenience factory function
def create_logger(
    component: str,
    level: int = logging.INFO
) -> StructuredLogger:
    """
    Factory function to create configured StructuredLogger.

    Args:
        component: Component identifier
        level: Logging level (default: INFO)

    Returns:
        Configured StructuredLogger instance

    Example:
        >>> logger = create_logger("processor", level=logging.DEBUG)
    """
    return StructuredLogger(component=component, level=level)
