"""
Cupertino Zone Monitor v2.0
============================

Bounded Context: Zone monitoring for video analytics.

Design Philosophy:
- Separation of Concerns: Geometry, Analytics, Rendering separated
- KISS: Simple para leer, no simple para escribir una vez
- Complejidad por diseño: Cada módulo tiene responsabilidad clara
- Pragmatismo > Purismo: Usamos supervision.geometry, no reinventamos

Architecture:

    cupertino_zone/
    ├── geometry/          # Pure geometry (immutable, stateless)
    │   ├── shapes.py      # PolygonZone, LineZone
    │   └── detector.py    # ZoneDetector (stateless detection logic)
    │
    ├── analytics/         # Statistics & counting (stateful)
    │   ├── counter.py     # ZoneCounter, ZoneStats
    │   └── tracker.py     # CrossingTracker (line crossing state)
    │
    ├── rendering/         # Visualization (stateless drawing)
    │   └── visualizer.py  # ZoneVisualizer
    │
    └── pipeline.py        # Orchestration (uses new architecture)

Usage:

    # 1. Create geometry (immutable)
    from cupertino_zone import PolygonZone, LineZone, ZoneDetector

    polygon = PolygonZone(
        vertices=np.array([[0,0], [100,0], [100,100], [0,100]]),
        frame_resolution_wh=(1920, 1080)
    )
    line = LineZone(start=(0, 500), end=(1920, 500))

    # 2. Detect (stateless)
    mask = ZoneDetector.detect_polygon(polygon, detections)
    crossed_in, crossed_out, state = ZoneDetector.detect_line_crossing(
        line, detections, tracker.state
    )

    # 3. Count (stateful)
    from cupertino_zone import ZoneCounter, CrossingTracker

    counter = ZoneCounter(zone_id="entrance")
    counter.update_polygon(mask, detections, class_names)
    stats = counter.get_stats()

    # 4. Visualize (stateless)
    from cupertino_zone import ZoneVisualizer

    visualizer = ZoneVisualizer()
    frame = visualizer.draw_polygon(frame, polygon, stats)

    # 5. Or use Pipeline (high-level orchestration)
    from cupertino_zone import PipelineBuilder

    pipeline = (
        PipelineBuilder()
        .with_video("video.mp4")
        .with_model(model)
        .add_polygon_zone("entrance", polygon)
        .add_line_zone("crossing", line)
        .build()
    )
    pipeline.process()
"""

# Geometry Layer (immutable, stateless)
from cupertino_zone.geometry.shapes import PolygonZone, LineZone
from cupertino_zone.geometry.detector import ZoneDetector

# Analytics Layer (stateful)
from cupertino_zone.analytics.counter import ZoneCounter, ZoneStats
from cupertino_zone.analytics.tracker import CrossingTracker

# Rendering Layer (stateless)
from cupertino_zone.rendering.visualizer import ZoneVisualizer

# Pipeline (orchestration)
from cupertino_zone.pipeline import ZoneMonitorPipeline, PipelineBuilder

__all__ = [
    # Geometry
    "PolygonZone",
    "LineZone",
    "ZoneDetector",
    # Analytics
    "ZoneCounter",
    "ZoneStats",
    "CrossingTracker",
    # Rendering
    "ZoneVisualizer",
    # Pipeline
    "ZoneMonitorPipeline",
    "PipelineBuilder",
]

__version__ = "2.0.0"
