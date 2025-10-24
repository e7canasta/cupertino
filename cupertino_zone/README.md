# Cupertino Zone Monitor

**KISS zone monitoring for computer vision** 🎸

## Design Philosophy

> "Un diseño limpio NO es un diseño complejo" - Ernesto

Aplicando **"Complejidad por Diseño"** del Manifiesto Visiona:
- **Cohesión > Ubicación**: Cada módulo = 1 bounded context
- **KISS ≠ Simplicidad Ingenua**: Simple para leer, no simplista
- **Pragmatismo > Purismo**: Usamos `supervision.geometry`, no reinventamos

## Architecture

```
cupertino_zone/
├── zone.py          # Bounded Context: Geometry + Detection
├── counter.py       # Bounded Context: Tracking + Statistics
├── visualizer.py    # Bounded Context: Drawing
└── pipeline.py      # Bounded Context: Orchestration
```

### Bounded Contexts (DDD)

1. **Zone** (`zone.py`):
   - Responsabilidad: Definición de zonas y detección punto-en-zona
   - Dependencias: `supervision.geometry`, `numpy`
   - Testeable: Pure functions, sin side effects

2. **Counter** (`counter.py`):
   - Responsabilidad: Conteo y agregación de estadísticas
   - Dependencias: `supervision.Detections`
   - Testeable: Stateful accumulator, immutable snapshots

3. **Visualizer** (`visualizer.py`):
   - Responsabilidad: Dibujado de zonas y estadísticas
   - Dependencias: `supervision.draw.utils`
   - Testeable: Idempotente (mismo input → mismo output)

4. **Pipeline** (`pipeline.py`):
   - Responsabilidad: Orquestación video processing
   - Dependencias: Todos los módulos anteriores
   - Testeable: Builder pattern, fail-fast validation

## Usage

### Basic Example

```python
from cupertino_zone import (
    PolygonZoneMonitor,
    ZoneVisualizer,
    PipelineBuilder,
)
from ultralytics import YOLO
import numpy as np
import supervision as sv

# 1. Define zone
polygon = np.array([[100, 200], [300, 200], [300, 400], [100, 400]])
zone = PolygonZoneMonitor(polygon, frame_resolution_wh=(1920, 1080))

# 2. Build pipeline
pipeline = (
    PipelineBuilder()
    .with_video("video.mp4")
    .with_model(YOLO("yolov8n.pt"))
    .add_zone(zone)
    .build()
)

# 3. Process
output_path = pipeline.process()
```

### Advanced: Line Crossing

```python
from cupertino_zone import LineZoneMonitor

# Define line
line = LineZoneMonitor(
    start=sv.Point(x=0, y=540),
    end=sv.Point(x=1920, y=540),
)

# Add to pipeline
pipeline.add_zone(line)
```

## Design Patterns Applied

### Builder Pattern
```python
pipeline = (
    PipelineBuilder()
    .with_video("input.mp4")
    .with_model(model)
    .add_zone(zone1)
    .add_zone(zone2)
    .build()  # Fail-fast validation
)
```

### Protocol (Duck Typing)
```python
class ZoneMonitor(Protocol):
    def trigger(self, detections: sv.Detections) -> np.ndarray:
        ...
```

### Immutable Value Objects
```python
@dataclass
class ZoneStats:
    total_count: int
    count_per_class: Dict[int, int]
```

## Comparison: Supervision vs Cupertino

| Feature | Supervision | Cupertino Zone |
|---------|-------------|----------------|
| **Scope** | General-purpose | Domain-specific (zone monitoring) |
| **API** | Many parameters | Builder pattern |
| **Crossing history** | Configurable deque | Simplified (last side only) |
| **Visualization** | Separate annotators | Integrated visualizer |
| **Dependencies** | Minimal | Uses supervision geometry |

**Trade-off aceptado**: Menos flexibilidad, más KISS para nuestro use case.

## Extension Points

### Custom Zone Types

Implement `ZoneMonitor` protocol:

```python
class CircleZoneMonitor:
    def trigger(self, detections: sv.Detections) -> np.ndarray:
        # Custom logic
        pass
```

### Custom Visualizations

Extend `ZoneVisualizer`:

```python
class HeatmapVisualizer(ZoneVisualizer):
    def draw_polygon_zone(self, frame, zone, stats):
        # Custom heatmap rendering
        pass
```

## Testing Strategy

1. **Zone Module**: Property tests (point-in-polygon invariants)
2. **Counter Module**: State-based tests (accumulation correctness)
3. **Visualizer Module**: Snapshot tests (rendering consistency)
4. **Pipeline Module**: Integration tests (end-to-end)

## Performance Considerations

- **Mask caching**: Polygon mask created once en `__init__`
- **NumPy vectorization**: Batch point checks
- **Frame stride**: Configurable para trade-off speed/accuracy

## Fail-Fast Principles

1. **Load-time validation**: Builder pattern checks en `build()`
2. **Type hints**: Mypy-compatible
3. **Clear errors**: `ValueError` con mensajes descriptivos

## References

- Manifiesto de Diseño: `MANIFESTO_DISENO - Blues Style.md`
- Supervision docs: `docs/supervision/`
- DDD: Bounded contexts, value objects, protocols

---

**Versión**: 1.0
**Autores**: Ernesto + Gaby
**Filosofía**: "Tocar blues con el código" 🎸
