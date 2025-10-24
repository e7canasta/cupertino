# cupertino_mqtt

**MQTT Communication Package for Cupertino Zone Monitoring**

Version: 1.0.0

---

## 🎯 Overview

`cupertino_mqtt` provides type-safe, production-ready MQTT messaging for the Cupertino zone monitoring system. It enables decoupled communication between the **Stream Processor** (inference + zone detection) and **RTSP Visualizer** (rendering).

### Architecture

```
Stream Processor                    RTSP Visualizer
(Inference + Zones)                 (Rendering)
       │                                   │
       ├─ DetectionPublisher               │
       │      └─→ MQTT Broker ─→ MessageSubscriber
       │                                   │
       └─ ZoneEventPublisher               │
              └─→ MQTT Broker ─→ MessageSubscriber
```

### Design Philosophy

- **Bounded Contexts**: schemas, publishers, logging
- **Type Safety**: Frozen dataclasses, type hints
- **Immutability**: Thread-safe, predictable
- **Observability**: JSON structured logging

---

## 📦 Installation

```bash
uv pip install -e .
```

**Dependencies**:
- `paho-mqtt>=1.6.1,<2.0` (MQTT client)

---

## 🚀 Quick Start

### 1. Start MQTT Broker

```bash
# Using Mosquitto
mosquitto -v

# Or with Docker
docker run -p 1883:1883 eclipse-mosquitto
```

### 2. Publisher (Stream Processor)

```python
from cupertino_mqtt import DetectionPublisher, create_logger
from cupertino_mqtt.schemas import Detection, DetectionMessage, BBox, Timestamp

# Create logger
logger = create_logger("processor")

# Create publisher
publisher = DetectionPublisher(
    broker_host="localhost",
    topic="cupertino/detections",
    logger=logger
)

# Connect
publisher.connect()

# Create detection message
det = Detection(
    tracker_id=1,
    class_name="person",
    confidence=0.95,
    bbox=BBox(x=100, y=200, width=50, height=100)
)

msg = DetectionMessage(
    schema_version="1.0",
    timestamp=Timestamp.now(),
    frame_id=123,
    source_id=0,
    detections=[det]
)

# Publish
publisher.publish_detection(msg)

# Disconnect when done
publisher.disconnect()
```

### 3. Subscriber (RTSP Visualizer)

```python
from cupertino_mqtt import MessageSubscriber, create_logger
from cupertino_mqtt.schemas import DetectionMessage, ZoneEventMessage

logger = create_logger("visualizer")

# Define callbacks
def on_detection(msg: DetectionMessage):
    print(f"Received {msg.detection_count} detections at frame {msg.frame_id}")
    for det in msg.detections:
        print(f"  - {det.class_name} (tracker_id={det.tracker_id})")

def on_zone_event(msg: ZoneEventMessage):
    print(f"Received {msg.zone_count} zone events at frame {msg.frame_id}")
    for zone in msg.zones:
        print(f"  - Zone {zone.zone_id}: {zone.event_type.value}")

# Create subscriber
subscriber = MessageSubscriber(
    broker_host="localhost",
    detection_topic="cupertino/detections",
    zone_event_topic="cupertino/zone_events",
    on_detection=on_detection,
    on_zone_event=on_zone_event,
    logger=logger
)

# Connect and start (non-blocking)
subscriber.connect()
subscriber.start()

# Your visualizer main loop
try:
    while True:
        # Render frames, etc.
        pass
except KeyboardInterrupt:
    subscriber.stop()
```

---

## 📋 Message Schemas

### Detection Message

```json
{
  "schema_version": "1.0",
  "timestamp": "2025-10-24T15:30:45.123456",
  "frame_id": 123,
  "source_id": 0,
  "detections": [
    {
      "tracker_id": 1,
      "class": "person",
      "confidence": 0.95,
      "bbox": {
        "x": 100.5,
        "y": 200.3,
        "width": 50.2,
        "height": 100.8
      }
    }
  ]
}
```

### Zone Event Message

```json
{
  "schema_version": "1.0",
  "timestamp": "2025-10-24T15:30:45.123456",
  "frame_id": 123,
  "source_id": 0,
  "zones": [
    {
      "zone_id": "entrance_zone",
      "zone_type": "polygon",
      "event_type": "inside",
      "stats": {
        "total_in": null,
        "total_out": null,
        "current_count": 2
      },
      "triggered_by": [1, 3]
    },
    {
      "zone_id": "doorway_line",
      "zone_type": "line",
      "event_type": "crossing",
      "crossing_direction": "in",
      "stats": {
        "total_in": 10,
        "total_out": 8,
        "current_count": null
      },
      "triggered_by": [1]
    }
  ]
}
```

---

## 🏗️ Module Structure

```
cupertino_mqtt/
├── __init__.py           # Public API
├── schemas/              # Data Structures
│   ├── common.py         # BBox, Timestamp
│   ├── detection.py      # Detection, DetectionMessage
│   └── zone_event.py     # ZoneEvent, ZoneEventMessage
├── publishers/           # Message Production
│   ├── base.py           # BasePublisher (abstract)
│   ├── detection.py      # DetectionPublisher
│   └── zone_event.py     # ZoneEventPublisher
├── subscriber.py         # Message Consumption
└── logging/              # Observability
    ├── events.py         # LogEvent (enum)
    └── structured.py     # StructuredLogger
```

---

## 📊 Structured Logging

All components emit JSON-structured logs for production observability:

```python
from cupertino_mqtt.logging import create_logger, LogEvent

logger = create_logger("my_component")

logger.info(
    event=LogEvent.DETECTION_PROCESSED,
    message="Processed 3 detections",
    metadata={'frame_id': 123, 'detection_count': 3}
)
```

**Output**:
```json
{
  "timestamp": "2025-10-24T15:30:45.123456",
  "level": "INFO",
  "component": "my_component",
  "event": "detection.processed",
  "message": "Processed 3 detections",
  "metadata": {"frame_id": 123, "detection_count": 3}
}
```

### Available Log Events

| Event | Description |
|-------|-------------|
| `MQTT_CONNECTED` | MQTT broker connection established |
| `MQTT_DISCONNECTED` | MQTT broker connection lost |
| `MQTT_PUBLISH_SUCCESS` | Message published successfully |
| `DETECTION_PROCESSED` | Detections processed from YOLO |
| `DETECTION_RECEIVED` | Detection message received |
| `ZONE_TRIGGERED` | Zone event triggered |
| `ZONE_EVENT_RECEIVED` | Zone event message received |
| `SERIALIZATION_ERROR` | Failed to serialize message |
| `DESERIALIZATION_ERROR` | Failed to deserialize message |

---

## 🧪 Testing

### Run Tests (Without Broker)

```bash
source .venv/bin/activate
python test_mqtt_pubsub.py
```

### Test with Real Broker

**Terminal 1** (Broker):
```bash
mosquitto -v
```

**Terminal 2** (Subscriber):
```bash
source .venv/bin/activate
mosquitto_sub -t "cupertino/#" -v
```

**Terminal 3** (Publisher):
```python
# Run your publisher code
```

---

## 🎯 Design Decisions

### Why QoS 0?

**Fire-and-forget** for high throughput (25 FPS):
- Temporal redundancy (next frame arrives in 40ms)
- Occasional loss is acceptable
- No acknowledgment overhead

Use **QoS 1** only for critical control messages.

### Why JSON instead of Protobuf?

- **Legible** for debugging
- **mosquitto_sub** works out-of-the-box
- **Drop-in replacement** if performance needed later

### Why Frozen Dataclasses?

- **Immutability**: Thread-safe, predictable
- **Type safety**: mypy compatible
- **Validation**: Fail-fast on construction
- **Performance**: Faster than Pydantic for 25 FPS

---

## 🚀 Next Steps

1. ✅ **Schemas implemented** (Detection, ZoneEvent)
2. ✅ **Publishers implemented** (DetectionPublisher, ZoneEventPublisher)
3. ✅ **Subscriber implemented** (MessageSubscriber)
4. ✅ **Structured logging** (JSON events)
5. ⏳ **Stream Processor** (InferencePipeline + cupertino_zone + MQTT)
6. ⏳ **RTSP Visualizer** (Subscriber + rendering)
7. ⏳ **go2rtc config** (RTSP simulation)

---

## 📚 Examples

See `test_mqtt_pubsub.py` for complete examples of:
- Serialization/deserialization
- Publisher usage
- Subscriber callbacks
- Error handling

---

## 🎸 Credits

Designed following the **"Blues Style" Manifesto**:
- **Cohesion > Location**: Each module has one reason to change
- **Type Safety**: Leverage Python typing
- **Pragmatism > Purismo**: Solve real problems
- **Simple to read, not simple to write once**

Built by: Ernesto (Visiona) + Gaby (AI Companion)

---

**Version**: 1.0.0
**License**: MIT (or your license)
**Python**: >=3.12
