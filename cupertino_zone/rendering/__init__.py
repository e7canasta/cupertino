"""
Rendering Layer
===============

Bounded Context: Zone visualization and drawing.

Responsibilities:
- Draw zones on frames (polygons, lines)
- Render statistics (counts, labels)
- Highlight detections in zones
- Pure rendering - no logic, no state

Non-responsibilities:
- Zone logic (handled by geometry)
- Counting (handled by analytics)
- Detection (handled by detector)

Design:
- Stateless drawing functions
- Uses supervision.draw.utils
- Configurable styles
"""

from cupertino_zone.rendering.visualizer import ZoneVisualizer

__all__ = [
    "ZoneVisualizer",
]

