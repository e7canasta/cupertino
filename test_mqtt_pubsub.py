"""
Test MQTT Pub/Sub (Without Real Broker)
========================================

This script tests the full publish/subscribe flow without requiring a real
MQTT broker, by simulating message passing.

Usage:
    source .venv/bin/activate && python test_mqtt_pubsub.py
"""

from cupertino_mqtt import (
    DetectionPublisher,
    ZoneEventPublisher,
    MessageSubscriber,
    create_logger,
)
from cupertino_mqtt.schemas import (
    Detection,
    DetectionMessage,
    BBox,
    Timestamp,
    ZoneEvent,
    ZoneEventMessage,
    ZoneType,
    EventType,
    ZoneStats,
    CrossingDirection,
)
import json


def test_message_serialization():
    """Test that messages can be serialized and deserialized."""
    print("\n" + "=" * 60)
    print("TEST: Message Serialization/Deserialization")
    print("=" * 60)

    logger = create_logger("test")

    # 1. Create Detection Publisher
    det_pub = DetectionPublisher(
        broker_host="localhost",
        topic="cupertino/detections",
        logger=logger,
    )
    print("\n✓ DetectionPublisher created")

    # 2. Create Detection Message
    det1 = Detection(
        tracker_id=1,
        class_name="person",
        confidence=0.95,
        bbox=BBox(x=100, y=200, width=50, height=100),
    )
    det2 = Detection(
        tracker_id=3,
        class_name="person",
        confidence=0.87,
        bbox=BBox(x=300, y=150, width=45, height=95),
    )

    det_msg = DetectionMessage(
        schema_version="1.0",
        timestamp=Timestamp.now(),
        frame_id=123,
        source_id=0,
        detections=[det1, det2],
    )
    print(f"✓ Created DetectionMessage with {det_msg.detection_count} detections")

    # 3. Serialize (what publisher does)
    serialized = det_pub.format_message(det_msg)
    json_str = json.dumps(serialized)
    print(f"✓ Serialized to JSON ({len(json_str)} bytes)")

    # 4. Deserialize (what subscriber does)
    deserialized_data = json.loads(json_str)
    reconstructed_msg = DetectionMessage.from_dict(deserialized_data)
    print(f"✓ Deserialized from JSON")

    # 5. Verify
    assert reconstructed_msg.frame_id == det_msg.frame_id
    assert reconstructed_msg.detection_count == det_msg.detection_count
    assert reconstructed_msg.detections[0].tracker_id == det1.tracker_id
    print("✓ Verification passed: Original == Reconstructed")

    # 6. Zone Event Test
    print("\n--- Zone Event Message ---")

    zone_pub = ZoneEventPublisher(
        broker_host="localhost",
        topic="cupertino/zone_events",
        logger=logger,
    )
    print("✓ ZoneEventPublisher created")

    zone1 = ZoneEvent(
        zone_id="entrance",
        zone_type=ZoneType.POLYGON,
        event_type=EventType.INSIDE,
        stats=ZoneStats(current_count=2),
        triggered_by=[1, 3],
    )

    zone2 = ZoneEvent(
        zone_id="doorway",
        zone_type=ZoneType.LINE,
        event_type=EventType.CROSSING,
        stats=ZoneStats(total_in=10, total_out=8),
        triggered_by=[1],
        crossing_direction=CrossingDirection.IN,
    )

    zone_msg = ZoneEventMessage(
        schema_version="1.0",
        timestamp=Timestamp.now(),
        frame_id=123,
        source_id=0,
        zones=[zone1, zone2],
    )
    print(f"✓ Created ZoneEventMessage with {zone_msg.zone_count} zones")

    # Serialize/Deserialize
    zone_serialized = zone_pub.format_message(zone_msg)
    zone_json_str = json.dumps(zone_serialized)
    zone_deserialized_data = json.loads(zone_json_str)
    zone_reconstructed = ZoneEventMessage.from_dict(zone_deserialized_data)

    assert zone_reconstructed.frame_id == zone_msg.frame_id
    assert zone_reconstructed.zone_count == zone_msg.zone_count
    assert zone_reconstructed.zones[0].zone_id == zone1.zone_id
    print("✓ Verification passed: Zone messages work")

    print("\n" + "=" * 60)
    print("✅ ALL SERIALIZATION TESTS PASSED")
    print("=" * 60)


def test_subscriber_callbacks():
    """Test subscriber callback invocation (simulated)."""
    print("\n" + "=" * 60)
    print("TEST: Subscriber Callbacks")
    print("=" * 60)

    logger = create_logger("test")

    # Track received messages
    received_detections = []
    received_zones = []

    def on_detection(msg: DetectionMessage):
        received_detections.append(msg)
        print(
            f"  📥 Detection callback: frame {msg.frame_id}, "
            f"{msg.detection_count} detections"
        )

    def on_zone_event(msg: ZoneEventMessage):
        received_zones.append(msg)
        print(
            f"  📥 Zone event callback: frame {msg.frame_id}, "
            f"{msg.zone_count} zones"
        )

    # Create subscriber
    subscriber = MessageSubscriber(
        broker_host="localhost",
        detection_topic="cupertino/detections",
        zone_event_topic="cupertino/zone_events",
        on_detection=on_detection,
        on_zone_event=on_zone_event,
        logger=logger,
    )
    print("✓ MessageSubscriber created with callbacks")

    # Simulate receiving messages (bypassing MQTT)
    print("\nSimulating message reception:")

    # Detection message
    det = Detection(
        tracker_id=1,
        class_name="person",
        confidence=0.95,
        bbox=BBox(x=100, y=200, width=50, height=100),
    )
    det_msg = DetectionMessage(
        schema_version="1.0",
        timestamp=Timestamp.now(),
        frame_id=456,
        source_id=0,
        detections=[det],
    )
    subscriber._handle_detection_message(det_msg.to_dict())

    # Zone event message
    zone = ZoneEvent(
        zone_id="test_zone",
        zone_type=ZoneType.POLYGON,
        event_type=EventType.INSIDE,
        stats=ZoneStats(current_count=1),
        triggered_by=[1],
    )
    zone_msg = ZoneEventMessage(
        schema_version="1.0",
        timestamp=Timestamp.now(),
        frame_id=456,
        source_id=0,
        zones=[zone],
    )
    subscriber._handle_zone_event_message(zone_msg.to_dict())

    # Verify callbacks were invoked
    assert len(received_detections) == 1
    assert len(received_zones) == 1
    assert received_detections[0].frame_id == 456
    assert received_zones[0].frame_id == 456

    print("\n✓ Callbacks invoked correctly")
    print(f"✓ Received {len(received_detections)} detection messages")
    print(f"✓ Received {len(received_zones)} zone event messages")

    # Check stats
    stats = subscriber.get_stats()
    print(f"\n✓ Subscriber stats:")
    print(f"  Detections: {stats['detections_received']}")
    print(f"  Zone events: {stats['zone_events_received']}")

    print("\n" + "=" * 60)
    print("✅ ALL CALLBACK TESTS PASSED")
    print("=" * 60)


def main():
    """Run all tests."""
    print("\n🎸 cupertino_mqtt - Pub/Sub Integration Tests")
    print("=" * 60)
    print("Testing without real MQTT broker (simulated)")
    print("=" * 60)

    try:
        test_message_serialization()
        test_subscriber_callbacks()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n🎯 Next Steps:")
        print("   1. Start MQTT broker: mosquitto -v")
        print("   2. Test with real broker (publisher + subscriber)")
        print("   3. Implement Stream Processor")
        print("   4. Implement RTSP Visualizer")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
