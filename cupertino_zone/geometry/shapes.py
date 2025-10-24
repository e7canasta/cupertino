"""
Geometric Shapes Module
========================

Pure geometric representations - NO state, NO side effects.

Design:
- Immutable shapes (frozen dataclass pattern)
- Mask-based polygon for O(1) point queries
- Cross-product for line side calculation
- Thread-safe by design (immutability)
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class PolygonZone:
    """
    Immutable polygon geometry with mask-based point-in-polygon.

    Design:
    - Mask created once at init (O(N) construction, O(1) queries)
    - Immutable by frozen dataclass
    - Thread-safe (no mutable state)

    Attributes:
        vertices: Nx2 array of (x, y) polygon vertices
        frame_resolution_wh: (width, height) for mask creation
    """

    vertices: np.ndarray
    frame_resolution_wh: Tuple[int, int]

    def __post_init__(self):
        """Create mask and validate inputs."""
        # Validate vertices
        if not isinstance(self.vertices, np.ndarray):
            raise TypeError(f"vertices must be np.ndarray, got {type(self.vertices)}")
        if self.vertices.ndim != 2 or self.vertices.shape[1] != 2:
            raise ValueError(f"vertices must be Nx2 array, got shape {self.vertices.shape}")
        if len(self.vertices) < 3:
            raise ValueError(f"Polygon must have at least 3 vertices, got {len(self.vertices)}")

        # Validate resolution
        width, height = self.frame_resolution_wh
        if width <= 0 or height <= 0:
            raise ValueError(f"frame_resolution_wh must be positive, got {self.frame_resolution_wh}")

        # Create mask (using object.__setattr__ for frozen dataclass)
        mask = self._create_mask()
        object.__setattr__(self, '_mask', mask)

        # Make vertices read-only
        self.vertices.flags.writeable = False

    def _create_mask(self) -> np.ndarray:
        """
        Create binary mask from polygon.

        Uses cv2.fillPoly for efficient rasterization.

        Returns:
            Boolean mask where True = inside polygon
        """
        import cv2

        width, height = self.frame_resolution_wh
        mask = np.zeros((height, width), dtype=np.uint8)

        # Reshape for cv2.fillPoly: (N, 1, 2)
        cv2_polygon = self.vertices.reshape((-1, 1, 2)).astype(np.int32)
        cv2.fillPoly(mask, [cv2_polygon], color=1)

        return mask.astype(bool)

    def contains_point(self, point: Tuple[float, float]) -> bool:
        """
        Check if point is inside polygon (O(1) via mask lookup).

        Args:
            point: (x, y) coordinates

        Returns:
            True if point is inside polygon, False otherwise
        """
        x, y = int(point[0]), int(point[1])

        # Bounds check
        width, height = self.frame_resolution_wh
        if not (0 <= x < width and 0 <= y < height):
            return False

        return bool(self._mask[y, x])


@dataclass(frozen=True)
class LineZone:
    """
    Immutable line segment for crossing detection.

    Design:
    - Cross product for side calculation (deterministic, no state)
    - Immutable geometry
    - Thread-safe

    Attributes:
        start: (x, y) line start point
        end: (x, y) line end point
    """

    start: Tuple[float, float]
    end: Tuple[float, float]

    def __post_init__(self):
        """Validate line segment."""
        if self.start == self.end:
            raise ValueError("Line start and end must be different points")

        # Precompute line vector (using object.__setattr__ for frozen)
        vector = np.array([
            self.end[0] - self.start[0],
            self.end[1] - self.start[1]
        ])
        object.__setattr__(self, '_vector', vector)

    def get_side(self, point: Tuple[float, float]) -> int:
        """
        Determine which side of the line a point is on.

        Uses cross product: (end - start) × (point - start)

        Args:
            point: (x, y) coordinates to test

        Returns:
            1: left side of line (cross product > 0)
            -1: right side of line (cross product < 0)
            0: on the line (cross product == 0)
        """
        # Vector from start to point
        to_point = np.array([
            point[0] - self.start[0],
            point[1] - self.start[1]
        ])

        # Cross product determines side
        cross = np.cross(self._vector, to_point)

        if cross > 0:
            return 1  # Left side
        elif cross < 0:
            return -1  # Right side
        else:
            return 0  # On line
