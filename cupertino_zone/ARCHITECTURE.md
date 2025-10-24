# Cupertino Zone Architecture

**"Complejidad por Diseño" en acción** 🎸

## Bounded Contexts (DDD)

```
┌─────────────────────────────────────────────────────────────┐
│                    cupertino_zone                            │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   zone.py    │  counter.py  │visualizer.py │  pipeline.py   │
│              │              │              │                │
│  Geometry +  │  Tracking +  │   Drawing    │ Orchestration  │
│  Detection   │  Statistics  │              │                │
└──────────────┴──────────────┴──────────────┴────────────────┘
```

### 1. Zone Module (`zone.py`)

**Bounded Context**: Geometry + Object-in-Zone Detection

```python
┌──────────────────────────────────────┐
│        ZoneMonitor (Protocol)        │
│  ┌────────────────────────────────┐  │
│  │ is_inside(point) -> bool       │  │
│  │ trigger(detections) -> ndarray │  │
│  └────────────────────────────────┘  │
└──────────────┬───────────────────────┘
               │
       ┌───────┴────────┐
       │                │
┌──────▼──────┐  ┌─────▼──────┐
│ PolygonZone │  │  LineZone  │
│   Monitor   │  │  Monitor   │
└─────────────┘  └────────────┘
```

**Responsibilities**:
- Polygon/Line geometry definition
- Point-in-polygon checks (using mask for performance)
- Crossing detection (directional)

**Dependencies**:
- `supervision.Point` (geometry primitives)
- `numpy` (array operations)
- `cv2` (mask creation)

**Testability**: ✅ Pure functions, property-based tests

---

### 2. Counter Module (`counter.py`)

**Bounded Context**: Statistics Tracking

```python
┌─────────────────────────────────┐
│         ZoneCounter             │
│  ┌───────────────────────────┐  │
│  │ update(detections, mask)  │  │
│  │ get_stats() -> ZoneStats  │  │
│  │ reset()                   │  │
│  └───────────────────────────┘  │
└─────────────┬───────────────────┘
              │
              │ produces
              ▼
     ┌────────────────┐
     │   ZoneStats    │  (Immutable Value Object)
     │ ┌────────────┐ │
     │ │total_count │ │
     │ │per_class   │ │
     │ └────────────┘ │
     └────────────────┘
```

**Responsibilities**:
- Aggregate counts (total, per-class)
- Immutable statistics snapshots
- Reset functionality

**Dependencies**:
- `supervision.Detections`
- `typing` (type hints)

**Testability**: ✅ State-based tests, immutable outputs

---

### 3. Visualizer Module (`visualizer.py`)

**Bounded Context**: Drawing

```python
┌────────────────────────────────────────┐
│         ZoneVisualizer                 │
│  ┌──────────────────────────────────┐  │
│  │ draw_polygon_zone(frame, zone)   │  │
│  │ draw_line_zone(frame, zone)      │  │
│  │ draw_detections_in_zone(...)     │  │
│  └──────────────────────────────────┘  │
└──────────────┬─────────────────────────┘
               │
               │ uses
               ▼
    supervision.draw.utils
    ┌───────────────────┐
    │ draw_filled_polygon│
    │ draw_polygon       │
    │ draw_line          │
    │ draw_text          │
    └───────────────────┘
```

**Responsibilities**:
- Render zones on frames
- Display statistics (text)
- Highlight in-zone detections

**Dependencies**:
- `supervision.draw.utils` (consistent API)
- `supervision.Color`, `Point`, `Rect`

**Testability**: ✅ Snapshot tests, idempotent

---

### 4. Pipeline Module (`pipeline.py`)

**Bounded Context**: Orchestration

```python
┌─────────────────────────────────────────┐
│       PipelineBuilder (Fluent API)      │
│  ┌───────────────────────────────────┐  │
│  │ .with_video(path)                 │  │
│  │ .with_model(model)                │  │
│  │ .add_zone(zone)                   │  │
│  │ .build() -> ZoneMonitorPipeline   │  │
│  └───────────────────────────────────┘  │
└──────────────┬──────────────────────────┘
               │
               │ builds
               ▼
   ┌─────────────────────────────┐
   │  ZoneMonitorPipeline        │
   │  ┌───────────────────────┐  │
   │  │ process() -> str      │  │
   │  └───────────────────────┘  │
   └──────────────┬──────────────┘
                  │
                  │ orchestrates
                  │
      ┌───────────┼───────────┐
      │           │           │
  Detection    Tracking    Zones
  (YOLO)     (ByteTrack) (Monitors)
      │           │           │
      └───────────┼───────────┘
                  │
              Visualization
```

**Responsibilities**:
- Coordinate video I/O (`VideoSink`, `get_video_frames_generator`)
- Orchestrate detection → tracking → zone processing → visualization
- Builder pattern for configuration
- Fail-fast validation

**Dependencies**:
- All other modules
- `supervision` (video utils, ByteTrack)
- `ultralytics` (YOLO - injectable)

**Testability**: ✅ Integration tests, mocking injected dependencies

---

## Design Patterns Applied

### 1. Builder Pattern

```python
pipeline = (
    PipelineBuilder()
    .with_video("input.mp4")
    .with_model(YOLO("yolov8n.pt"))
    .add_zone(polygon_zone)
    .add_zone(line_zone)
    .with_visualizer(visualizer)
    .build()  # ← Fail-fast validation
)
```

**Beneficios**:
- Fluent API (readable configuration)
- Immutable `PipelineConfig` after `build()`
- Validation centralizada

---

### 2. Protocol (Duck Typing)

```python
class ZoneMonitor(Protocol):
    def trigger(self, detections: sv.Detections) -> np.ndarray:
        ...
```

**Beneficios**:
- Polimorfismo sin herencia
- Extensible (custom zone types)
- Type-safe (mypy)

---

### 3. Immutable Value Objects

```python
@dataclass
class ZoneStats:
    total_count: int
    count_per_class: Dict[int, int]
```

**Beneficios**:
- No side effects
- Thread-safe
- Easy to test

---

## Data Flow

```
┌──────────────┐
│ Video Frames │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ YOLO Model   │ (Detection)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  ByteTrack   │ (Tracking)
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ ZoneMonitor  │ (trigger)
│  .trigger()  │
└──────┬───────┘
       │
       ├─► ZoneCounter.update()  → ZoneStats
       │
       └─► ZoneVisualizer.draw() → Annotated Frame
                                        │
                                        ▼
                                  ┌─────────────┐
                                  │ VideoSink   │
                                  └─────────────┘
```

---

## Comparison: Supervision vs Cupertino

| Aspect | Supervision | Cupertino Zone |
|--------|-------------|----------------|
| **Scope** | General-purpose CV utilities | Domain-specific (zone monitoring) |
| **Zones** | `PolygonZone`, `LineZone` with full history | Simplified, KISS approach |
| **API** | Annotator classes | Integrated `ZoneVisualizer` |
| **Config** | Many constructor params | Builder pattern |
| **Crossing** | Configurable deque history | Last-side tracking only |
| **Deps** | Standalone | Uses supervision.geometry |

**Trade-off**: Menos features, más KISS para nuestro caso de uso.

---

## Extension Points

### Custom Zone Types

```python
class CircleZoneMonitor:
    def trigger(self, detections: sv.Detections) -> np.ndarray:
        # Custom circle-based detection
        pass
```

### Custom Visualizations

```python
class HeatmapVisualizer(ZoneVisualizer):
    def draw_polygon_zone(self, frame, zone, stats):
        # Heatmap rendering
        pass
```

---

## Metrics

| Metric | Value | Notes |
|--------|-------|-------|
| **Modules** | 4 | 1 per bounded context |
| **LOC per module** | ~150 | KISS threshold |
| **Cohesion** | ⭐⭐⭐⭐⭐ | 1 module = 1 responsibility |
| **Coupling** | ⭐⭐⭐⭐ | Low (protocol-based) |
| **Testability** | ⭐⭐⭐⭐⭐ | Pure functions, immutable data |

---

## References

- **Manifiesto**: `MANIFESTO_DISENO - Blues Style.md`
- **Supervision Docs**: `docs/supervision/`
- **DDD**: Evans, "Domain-Driven Design"
- **Builder Pattern**: Gang of Four

---

**Filosofía**: *"Simple para leer, no simple para escribir una vez"* 🎸
