"""
Common Schema Types
==================

Bounded Context: Shared Data Structures

This module defines common types used across detection and zone event messages.

Design Principles:
- Immutability: frozen=True prevents accidental mutation
- Type Safety: All fields explicitly typed
- Serialization: to_dict() for JSON export
- Validation: Constructor validates invariants

Types:
- BBox: Bounding box with normalized or absolute coordinates
- Timestamp: ISO 8601 timestamp wrapper
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any


@dataclass(frozen=True)
class BBox:
    """
    Immutable bounding box representation.

    Coordinates are in absolute pixel values (not normalized).
    Origin is top-left corner of frame.

    Attributes:
        x: Left edge x-coordinate (pixels)
        y: Top edge y-coordinate (pixels)
        width: Box width (pixels)
        height: Box height (pixels)

    Invariants:
        - width > 0
        - height > 0

    Example:
        >>> bbox = BBox(x=100.5, y=200.3, width=50.2, height=100.8)
        >>> bbox.to_dict()
        {'x': 100.5, 'y': 200.3, 'width': 50.2, 'height': 100.8}
    """
    x: float
    y: float
    width: float
    height: float

    def __post_init__(self):
        """Validate invariants."""
        if self.width <= 0:
            raise ValueError(f"BBox width must be > 0, got {self.width}")
        if self.height <= 0:
            raise ValueError(f"BBox height must be > 0, got {self.height}")

    def to_dict(self) -> Dict[str, float]:
        """Serialize to JSON-compatible dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'BBox':
        """Deserialize from dict.

        Args:
            data: Dictionary with keys: x, y, width, height

        Returns:
            BBox instance

        Raises:
            ValueError: If required keys missing or invalid values
        """
        try:
            return cls(
                x=float(data['x']),
                y=float(data['y']),
                width=float(data['width']),
                height=float(data['height'])
            )
        except KeyError as e:
            raise ValueError(f"Missing required BBox field: {e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid BBox data: {e}")

    @property
    def center_x(self) -> float:
        """Center x-coordinate."""
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        """Center y-coordinate."""
        return self.y + self.height / 2

    @property
    def area(self) -> float:
        """Bounding box area in square pixels."""
        return self.width * self.height


@dataclass(frozen=True)
class Timestamp:
    """
    Immutable ISO 8601 timestamp wrapper.

    Provides type-safe timestamp handling with serialization.

    Attributes:
        value: ISO 8601 formatted timestamp string

    Example:
        >>> ts = Timestamp.now()
        >>> ts.value
        '2025-10-24T15:30:45.123456'
    """
    value: str

    @classmethod
    def now(cls) -> 'Timestamp':
        """Create timestamp from current time."""
        return cls(value=datetime.utcnow().isoformat())

    @classmethod
    def from_datetime(cls, dt: datetime) -> 'Timestamp':
        """Create timestamp from datetime object."""
        return cls(value=dt.isoformat())

    def to_datetime(self) -> datetime:
        """Parse to datetime object.

        Returns:
            datetime instance

        Raises:
            ValueError: If timestamp format invalid
        """
        try:
            return datetime.fromisoformat(self.value)
        except ValueError as e:
            raise ValueError(f"Invalid ISO timestamp: {self.value}") from e

    def to_dict(self) -> str:
        """Serialize to JSON (as string)."""
        return self.value
