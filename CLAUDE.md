# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
Computer vision kata project focused on object detection and tracking using **Supervision** and **Ultralytics YOLO**.

### Main Components
- `main.py`: ByteTrack line-crossing counter for video analysis
- `run_crop_image.py`: Image preprocessing utilities (crop, scale, resize, letterbox)
- `run_draw.py`: Animated shape drawing demo with ShapeAnimator
- `cupertino_zone/`: KISS zone monitoring package (DDD bounded contexts)

## Development Commands

### Environment Setup
```bash
uv sync                          # Install dependencies from pyproject.toml
```

### Running Scripts
```bash
uv run python main.py                # Video tracking pipeline (vehicles-1280x720.mp4)
uv run python run_crop_image.py      # Image preprocessing demo
uv run python run_draw.py            # Animated car drawing demo
uv run python run_zone_monitor.py   # Zone monitoring demo (polygon + line zones)
```

### Testing
Manual testing approach (pair-programming style). Run scripts and verify output manually. When adding tests:
- Use `pytest` framework
- Place in `tests/` directory
- Name pattern: `test_<feature>.py`
- Verify compilation as minimum test

## Architecture & Design Philosophy

### Project Structure
```
cupertino/
├── data/                # Video and image assets (not version controlled)
├── samples/             # Generated output artifacts
├── runs/                # Timestamped output folders
├── cupertino_zone/      # Zone monitoring package (DDD architecture)
│   ├── zone.py          # Bounded Context: Geometry + Detection
│   ├── counter.py       # Bounded Context: Tracking + Statistics
│   ├── visualizer.py    # Bounded Context: Drawing
│   └── pipeline.py      # Bounded Context: Orchestration
├── main.py              # Video tracking with ByteTrack + LineZone
├── run_crop_image.py    # Image utilities exploration
├── run_draw.py          # Animated shapes (ShapeAnimator pattern)
└── run_zone_monitor.py  # Zone monitoring demo
```

### Key Technical Patterns

**main.py** implements a tracking pipeline:
1. Frame generator (`sv.get_video_frames_generator`)
2. ByteTrack tracker for persistent object IDs
3. LineZone for counting crossing events (in/out)
4. Ultralytics model integration via `sv.Detections.from_ultralytics`

**run_crop_image.py** demonstrates supervision utilities:
- Display detection with matplotlib backend switching
- Multiple image transformations (crop, overlay, scale, resize, letterbox)
- Environment-aware plotting (DISPLAY var check)

**run_draw.py** demonstrates animated drawing:
- `ShapeAnimator` class encapsulates animation logic (SRP)
- Uses `supervision.draw.utils` API (filled polygons, rectangles, text)
- Animated car moving across video frames

**cupertino_zone/** package (DDD architecture):
- **zone.py**: `PolygonZoneMonitor`, `LineZoneMonitor` - geometry + detection
- **counter.py**: `ZoneCounter`, `ZoneStats` - immutable statistics
- **visualizer.py**: `ZoneVisualizer` - uses `supervision.draw` primitives
- **pipeline.py**: `ZoneMonitorPipeline` + Builder pattern - orchestration

Key patterns:
- **Builder Pattern**: Fluent API for pipeline construction (`PipelineBuilder`)
- **Protocol (Duck Typing)**: `ZoneMonitor` interface for polymorphism
- **Immutable Value Objects**: `ZoneStats` dataclass
- **Fail Fast**: Validation in `build()`, not runtime

### Known Issues in Current Code

**main.py:6** - Missing `=` operator in assignment:
```python
frames_generator sv.get_video_frames_generator(...)  # Should be frames_generator =
```

**main.py:20** - Undefined `model` variable (needs initialization)

**main.py:30** - Typo: `linze_zone` should be `line_zone`

## Design Principles
- **Complejidad por diseño, no por accidente**: Attack complexity through architecture, not complicated code
- **Cohesión > Ubicación**: Modules defined by conceptual cohesion, not size
- **Fail Fast**: Load-time validation preferred over runtime debugging
- Pragmatism over purism - simple version first, patterns when needed

## Commit Guidelines
- Co-authored commits with: `Co-Authored-By: Gaby <noreply@anthropic.com>`
- Imperative subject lines (72 chars max)
- No "Generated with Claude Code" footers
- Reference visual changes with sample outputs

## Dependencies
- `pillow>=12.0.0` - Image I/O
- `supervision>=0.26.1` - CV utilities, tracking, zones
- `ultralytics>=8.3.220` - YOLO models

Python 3.12+ required (see pyproject.toml)
