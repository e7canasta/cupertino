"""
Cupertino Zone Monitor
======================

Bounded Context: Zone monitoring for video analytics.

Design Philosophy:
- KISS: Simple para leer, no simple para escribir una vez
- Complejidad por diseño: Cada módulo tiene responsabilidad clara
- Pragmatismo > Purismo: Usamos supervision.geometry, no reinventamos

Modules:
- zone: Zone definition and detection logic
- counter: Object counting and tracking
- visualizer: Drawing zones and counts
- pipeline: Video processing orchestration
"""

from cupertino_zone.zone import PolygonZoneMonitor, LineZoneMonitor
from cupertino_zone.counter import ZoneCounter, ZoneStats
from cupertino_zone.visualizer import ZoneVisualizer
from cupertino_zone.pipeline import ZoneMonitorPipeline, PipelineBuilder

__all__ = [
    "PolygonZoneMonitor",
    "LineZoneMonitor",
    "ZoneCounter",
    "ZoneStats",
    "ZoneVisualizer",
    "ZoneMonitorPipeline",
    "PipelineBuilder",
]
