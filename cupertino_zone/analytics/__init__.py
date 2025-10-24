"""
Analytics Layer
===============

Bounded Context: Stateful counting and statistics tracking.

Responsibilities:
- Accumulate counts over time (mutable state)
- Track crossing history (line zones)
- Generate immutable statistics snapshots
- Classwise counting

Design Philosophy:
- Mutable accumulators (ZoneCounter, CrossingTracker)
- Immutable outputs (ZoneStats)
- Thread-safe via encapsulation
- Clear state management
"""

from cupertino_zone.analytics.counter import ZoneCounter, ZoneStats
from cupertino_zone.analytics.tracker import CrossingTracker

__all__ = [
    "ZoneCounter",
    "ZoneStats",
    "CrossingTracker",
]
