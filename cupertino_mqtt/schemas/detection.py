"""
Detection Message Schema
========================

Bounded Context: Detection Data Structures

This module defines the schema for YOLO detection messages published via MQTT.

Design:
- Detection: Single object detection with tracking
- DetectionMessage: Complete message with metadata
- Immutable (frozen dataclasses)
- Type-safe serialization/deserialization

Message Flow:
    YOLO Inference → Detection → DetectionPublisher → MQTT → Subscriber → Visualizer
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from .common import BBox, Timestamp


@dataclass(frozen=True)
class Detection:
    """
    Single object detection with tracking information.

    Represents one detected object from YOLO with ByteTrack tracking ID.

    Attributes:
        tracker_id: Persistent tracking ID from ByteTrack (required for line crossing)
        class_name: Object class (e.g., "person", "vehicle")
        confidence: Detection confidence score [0.0, 1.0]
        bbox: Bounding box coordinates (absolute pixels)

    Invariants:
        - confidence in [0.0, 1.0]
        - tracker_id >= 0

    Example:
        >>> det = Detection(
        ...     tracker_id=1,
        ...     class_name="person",
        ...     confidence=0.95,
        ...     bbox=BBox(x=100, y=200, width=50, height=100)
        ... )
    """
    tracker_id: int
    class_name: str
    confidence: float
    bbox: BBox

    def __post_init__(self):
        """Validate invariants."""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"Confidence must be in [0.0, 1.0], got {self.confidence}"
            )
        if self.tracker_id < 0:
            raise ValueError(
                f"Tracker ID must be >= 0, got {self.tracker_id}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            'tracker_id': self.tracker_id,
            'class': self.class_name,
            'confidence': self.confidence,
            'bbox': self.bbox.to_dict()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Detection':
        """Deserialize from dict.

        Args:
            data: Dictionary with detection fields

        Returns:
            Detection instance

        Raises:
            ValueError: If required fields missing or invalid
        """
        try:
            return cls(
                tracker_id=int(data['tracker_id']),
                class_name=str(data['class']),
                confidence=float(data['confidence']),
                bbox=BBox.from_dict(data['bbox'])
            )
        except KeyError as e:
            raise ValueError(f"Missing required Detection field: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid Detection data: {e}")


@dataclass(frozen=True)
class DetectionMessage:
    """
    Complete detection message for MQTT publication.

    Contains all detections from a single frame with metadata.

    Attributes:
        schema_version: Message schema version (for evolution)
        timestamp: ISO 8601 timestamp of message creation
        frame_id: Sequential frame number
        source_id: Video source identifier (for multi-camera)
        detections: List of detected objects

    Example:
        >>> msg = DetectionMessage(
        ...     schema_version="1.0",
        ...     timestamp=Timestamp.now(),
        ...     frame_id=123,
        ...     source_id=0,
        ...     detections=[det1, det2]
        ... )
        >>> json_data = msg.to_dict()
    """
    schema_version: str
    timestamp: Timestamp
    frame_id: int
    source_id: int
    detections: List[Detection] = field(default_factory=list)

    def __post_init__(self):
        """Validate invariants."""
        if self.frame_id < 0:
            raise ValueError(f"Frame ID must be >= 0, got {self.frame_id}")
        if self.source_id < 0:
            raise ValueError(f"Source ID must be >= 0, got {self.source_id}")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict.

        Returns:
            Dictionary ready for json.dumps()
        """
        return {
            'schema_version': self.schema_version,
            'timestamp': self.timestamp.to_dict(),
            'frame_id': self.frame_id,
            'source_id': self.source_id,
            'detections': [det.to_dict() for det in self.detections]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DetectionMessage':
        """Deserialize from dict.

        Args:
            data: Dictionary with message fields

        Returns:
            DetectionMessage instance

        Raises:
            ValueError: If required fields missing or invalid
        """
        try:
            return cls(
                schema_version=str(data['schema_version']),
                timestamp=Timestamp(value=data['timestamp']),
                frame_id=int(data['frame_id']),
                source_id=int(data['source_id']),
                detections=[
                    Detection.from_dict(det)
                    for det in data.get('detections', [])
                ]
            )
        except KeyError as e:
            raise ValueError(f"Missing required DetectionMessage field: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid DetectionMessage data: {e}")

    @property
    def detection_count(self) -> int:
        """Number of detections in this message."""
        return len(self.detections)

    def get_detections_by_class(self, class_name: str) -> List[Detection]:
        """Filter detections by class name.

        Args:
            class_name: Class to filter (e.g., "person")

        Returns:
            List of detections matching class
        """
        return [det for det in self.detections if det.class_name == class_name]

    def get_tracker_ids(self) -> List[int]:
        """Extract all tracker IDs from detections.

        Returns:
            List of tracker IDs (may contain duplicates if tracking failed)
        """
        return [det.tracker_id for det in self.detections]
