"""
Stream Processor Service - Main inference pipeline orchestrator.

This module provides the StreamProcessorService class which orchestrates
the complete video processing pipeline: RTSP stream consumption, YOLO
inference, zone monitoring, and MQTT publishing.

Architecture:
- Uses InferencePipeline.init_with_custom_logic() for full control
- Custom inference logic in on_video_frame()
- MQTT publishing in dedicated thread
- Thread-safe zone registry and model swapping

Threading Model:
- Video Source Thread (InferencePipeline internal)
- Inference Thread (InferencePipeline internal, calls on_video_frame)
- Dispatch Thread (InferencePipeline internal, calls on_prediction)
- MQTT Publisher Thread (our thread)
- Control Plane Thread (paho-mqtt internal, command handlers)
"""

import threading
import queue
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

import numpy as np
import supervision as sv
from inference import InferencePipeline
from inference.core.interfaces.camera.entities import VideoFrame

# New cupertino_zone API (v2.0)
from cupertino_zone import PolygonZone, LineZone, ZoneDetector
from cupertino_zone.analytics import ZoneCounter, CrossingTracker
from cupertino_processor.config import ProcessorConfig, ZoneConfig
from cupertino_processor.registry import ZoneMonitorRegistry
from cupertino_processor.model_loader import ModelLoader

logger = logging.getLogger(__name__)


@dataclass
class FramePredictions:
    """
    Predictions for a single frame.

    This dataclass encapsulates all inference results and metadata for
    a processed video frame.
    """
    frame_id: int
    timestamp: float
    detections: sv.Detections
    zone_results: Dict[str, np.ndarray]
    zone_counts: Dict[str, int]


class StreamProcessorService:
    """
    Main stream processing service.

    This service orchestrates the complete video processing pipeline:
    1. RTSP stream consumption (via InferencePipeline)
    2. YOLO object detection (custom logic in on_video_frame)
    3. Zone monitoring (via ZoneMonitorRegistry)
    4. MQTT publishing (dedicated publisher thread)

    Threading Architecture:
    - InferencePipeline manages 3 internal threads:
      1. Video Source Thread (RTSP decode)
      2. Inference Thread (calls on_video_frame)
      3. Dispatch Thread (calls on_prediction)

    - We add 1 additional thread:
      4. MQTT Publisher Thread (publishes to MQTT)

    - Control Plane has 1 internal thread:
      5. paho-mqtt client thread (command handlers)

    Thread Safety:
    - zone_registry: Protected by internal lock
    - model: Protected by _model_lock
    - publish_queue: Thread-safe queue.Queue
    - tracker: NOT thread-safe, only accessed from Inference Thread

    Usage:
        config = ProcessorConfig.from_yaml("config.yaml")
        control_plane = MQTTControlPlane(...)
        detection_publisher = DetectionPublisher(...)
        zone_event_publisher = ZoneEventPublisher(...)

        service = StreamProcessorService(
            config=config,
            control_plane=control_plane,
            detection_publisher=detection_publisher,
            zone_event_publisher=zone_event_publisher,
        )

        service.setup()
        service.run()  # Blocks until stopped
    """

    def __init__(
        self,
        config: ProcessorConfig,
        control_plane,  # MQTTControlPlane
        detection_publisher,  # DetectionPublisher
        zone_event_publisher,  # ZoneEventPublisher
    ):
        """
        Initialize stream processor service.

        Args:
            config: Processor configuration
            control_plane: MQTT control plane for commands
            detection_publisher: Publisher for detection messages
            zone_event_publisher: Publisher for zone event messages
        """
        self.config = config
        self.control_plane = control_plane
        self.detection_publisher = detection_publisher
        self.zone_event_publisher = zone_event_publisher

        # Components
        self.zone_registry = ZoneMonitorRegistry()
        self.model_loader = ModelLoader(config.models_dir)

        # Model (mutable, protected by lock for hot-swap)
        self.model = None
        self._model_lock = threading.Lock()

        # Tracker (ByteTrack for tracking IDs)
        # NOT thread-safe - only accessed from Inference Thread
        self.tracker = sv.ByteTrack()

        # MQTT publishing
        self.publish_queue = queue.Queue(maxsize=512)
        self.publisher_thread = None
        self.stop_event = threading.Event()

        # Pipeline
        self.pipeline = None

        # Lifecycle state
        self._running = False
        self._stopped_event = threading.Event()

        logger.info(
            f"StreamProcessorService initialized for service_id={config.service_id}"
        )

    def _initialize_zones(self):
        """
        Initialize zones from configuration.

        This method loads all zones from config and adds them to the registry.
        Called during setup phase.
        """
        for zone_config in self.config.zones:
            zone = self._create_zone_from_config(zone_config)
            self.zone_registry.add_zone(zone_config.zone_id, zone)

            if not zone_config.enabled:
                self.zone_registry.disable_zone(zone_config.zone_id)

            logger.info(
                f"Initialized zone: {zone_config.zone_id} "
                f"(type={zone_config.zone_type}, enabled={zone_config.enabled})"
            )

    def _create_zone_from_config(self, zone_config: ZoneConfig):
        """
        Create a Zone from configuration (NEW API v2.0).

        Args:
            zone_config: Zone configuration

        Returns:
            PolygonZone or LineZone instance
        """
        coordinates = np.array(zone_config.coordinates, dtype=np.int32)

        if zone_config.zone_type == "polygon":
            zone = PolygonZone(
                vertices=coordinates,
                frame_resolution_wh=self.config.frame_resolution_wh
            )
            return zone

        elif zone_config.zone_type == "line":
            zone = LineZone(
                start=(float(coordinates[0][0]), float(coordinates[0][1])),
                end=(float(coordinates[1][0]), float(coordinates[1][1]))
            )
            return zone

        else:
            raise ValueError(f"Unknown zone_type: {zone_config.zone_type}")

    def _load_initial_model(self):
        """
        Load initial YOLO model from configuration.

        This method loads the model specified in config and sets it as current.
        Called during setup phase.
        """
        with self._model_lock:
            self.model = self.model_loader.load_model_from_config(
                self.config.model_config
            )

        model_info = self.model_loader.get_current_model_info()
        logger.info(f"Loaded initial model: {model_info}")

    def setup(self):
        """
        Setup the inference pipeline.

        This method initializes the InferencePipeline with custom logic,
        allowing us to control the inference process and integrate zone
        monitoring.

        Must be called before run().
        """
        # Initialize zones
        self._initialize_zones()

        # Load initial model
        self._load_initial_model()

        # Setup control plane command handlers
        self._setup_control_handlers()

        # Create pipeline with custom logic
        self.pipeline = InferencePipeline.init_with_custom_logic(
            video_reference=self.config.rtsp_url,
            on_video_frame=self.on_video_frame,
            on_prediction=self.on_prediction,
            max_fps=self.config.max_fps,
        )

        logger.info("Pipeline setup complete")

    def _setup_control_handlers(self):
        """
        Register command handlers with control plane.

        This method registers all supported commands with the control plane's
        command registry. Commands are handled by the Control Plane thread.
        """
        registry = self.control_plane.command_registry

        # Zone management commands
        registry.register(
            "add_zone",
            self._handle_add_zone,
            "Add a new zone"
        )
        registry.register(
            "remove_zone",
            self._handle_remove_zone,
            "Remove an existing zone"
        )
        registry.register(
            "enable_zone",
            self._handle_enable_zone,
            "Enable a zone"
        )
        registry.register(
            "disable_zone",
            self._handle_disable_zone,
            "Disable a zone"
        )
        registry.register(
            "list_zones",
            self._handle_list_zones,
            "List all zones"
        )

        # Model management commands
        registry.register(
            "set_model",
            self._handle_set_model,
            "Hot-swap YOLO model"
        )
        registry.register(
            "get_model",
            self._handle_get_model,
            "Get current model info"
        )

        logger.info("Control handlers registered")

    def start(self):
        """
        Start the stream processor service (non-blocking).

        This method starts all components and returns immediately.
        Use wait() to block until service stops.

        Lifecycle:
        1. Connect control plane
        2. Connect publishers
        3. Start MQTT publisher thread
        4. Start InferencePipeline (non-blocking)

        Returns:
            None
        """
        if self._running:
            logger.warning("Service already running")
            return

        logger.info("Starting stream processor service")

        # Connect control plane
        if not self.control_plane.connect(timeout=5.0):
            raise RuntimeError("Failed to connect to MQTT broker (control plane)")

        # Connect publishers
        self.detection_publisher.connect()
        self.zone_event_publisher.connect()

        # Start MQTT publisher thread
        self.publisher_thread = threading.Thread(
            target=self._publish_loop,
            name="MQTTPublisherThread",
            daemon=True
        )
        self.publisher_thread.start()
        logger.info("MQTT publisher thread started")

        # Start pipeline (non-blocking)
        self.pipeline.start()
        self._running = True

        # Publish running status
        self.control_plane.publish_status("running")
        logger.info("✅ Stream processor service started")

    def wait(self):
        """
        Block until service stops.

        This method blocks the calling thread until stop() is called
        or the pipeline terminates.
        """
        if not self._running:
            logger.warning("Service not running")
            return

        try:
            # Block until pipeline finishes
            self.pipeline.join()
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, stopping...")
            self.stop()
        finally:
            self._stopped_event.set()

    def stop(self):
        """
        Stop the stream processor service gracefully.

        This method stops all components and cleans up resources.

        Lifecycle:
        1. Stop InferencePipeline
        2. Stop MQTT publisher thread
        3. Disconnect publishers
        4. Disconnect control plane
        """
        if not self._running:
            logger.warning("Service not running")
            return

        logger.info("Stopping stream processor service")

        # Stop pipeline
        try:
            self.pipeline.terminate()
        except Exception as e:
            logger.error(f"Error stopping pipeline: {e}")

        # Stop publisher thread
        self.stop_event.set()
        if self.publisher_thread:
            self.publisher_thread.join(timeout=5.0)
            logger.info("MQTT publisher thread stopped")

        # Disconnect publishers
        self.detection_publisher.disconnect()
        self.zone_event_publisher.disconnect()

        # Publish stopped status and disconnect control plane
        self.control_plane.publish_status("stopped")
        self.control_plane.disconnect()

        self._running = False
        logger.info("✅ Stream processor service stopped")

    def run(self):
        """
        Run the stream processor service.

        This method starts the pipeline and publisher thread, then blocks
        until the stop event is set.

        Lifecycle:
        1. Start MQTT publisher thread
        2. Start InferencePipeline (blocks here)
        3. Wait for pipeline to finish
        4. Stop publisher thread
        5. Cleanup
        """
        logger.info("Starting stream processor service")

        # Start MQTT publisher thread
        self.publisher_thread = threading.Thread(
            target=self._publish_loop,
            name="MQTTPublisherThread",
            daemon=True
        )
        self.publisher_thread.start()
        logger.info("MQTT publisher thread started")

        # Start pipeline (blocks until stopped)
        try:
            self.pipeline.start()
            self.pipeline.join()
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
        finally:
            # Cleanup
            logger.info("Stopping publisher thread")
            self.stop_event.set()
            if self.publisher_thread:
                self.publisher_thread.join(timeout=5.0)

            logger.info("Stream processor service stopped")

    def on_video_frame(self, frames: List[VideoFrame]) -> List[Dict]:
        """
        Custom inference logic (called by InferencePipeline Inference Thread).

        This is where we have full control over the inference process:
        1. YOLO inference
        2. ByteTrack (tracking IDs)
        3. Zone monitoring
        4. Count updates

        Args:
            frames: List of video frames (length 1 for single stream)

        Returns:
            List of prediction dictionaries

        Thread: Inference Thread (InferencePipeline internal)
        """
        frame = frames[0]

        # 1. YOLO inference (thread-safe model access)
        with self._model_lock:
            model = self.model

        # Inference (GPU-bound, outside lock)
        results = model(
            frame.image,
            verbose=False,
            conf=self.config.model_config.confidence,
            iou=self.config.model_config.iou_threshold,
            max_det=self.config.model_config.max_detections,
        )[0]

        # Convert to supervision Detections
        detections = sv.Detections.from_ultralytics(results)

        # 2. ByteTrack (tracking IDs)
        # NOTE: tracker is NOT thread-safe, but only accessed from this thread
        detections = self.tracker.update_with_detections(detections)

        # 3. Zone monitoring (thread-safe via registry lock)
        zone_results = self.zone_registry.trigger(detections)

        # 4. Calculate zone counts
        # Note: PolygonZoneMonitor returns mask, LineZoneMonitor returns tuple (crossed_in, crossed_out)
        zone_counts = {}
        for zone_id, result in zone_results.items():
            if isinstance(result, tuple):
                # LineZoneMonitor: sum of crossings (in + out)
                crossed_in, crossed_out = result
                zone_counts[zone_id] = int(crossed_in.sum() + crossed_out.sum())
            else:
                # PolygonZoneMonitor: sum of detections in zone
                zone_counts[zone_id] = int(result.sum())

        # 5. Build predictions dict
        predictions = {
            "frame_id": frame.frame_id,
            "timestamp": frame.frame_timestamp,
            "detections": detections,
            "zone_results": zone_results,
            "zone_counts": zone_counts,
        }

        return [predictions]

    def on_prediction(self, predictions: List[Dict], frames: List[VideoFrame]):
        """
        MQTT publishing callback (called by InferencePipeline Dispatch Thread).

        This method builds MQTT messages and queues them for publishing.

        Args:
            predictions: List of prediction dicts (from on_video_frame)
            frames: List of video frames

        Thread: Dispatch Thread (InferencePipeline internal)
        """
        pred = predictions[0]
        frame = frames[0]

        # Build messages
        detection_msg = self._build_detection_message(pred, frame)
        zone_event_msg = self._build_zone_event_message(pred, frame)

        # Queue for publishing (thread-safe queue)
        try:
            self.publish_queue.put_nowait(("detection", detection_msg))
            self.publish_queue.put_nowait(("zone_event", zone_event_msg))
        except queue.Full:
            logger.warning("Publish queue full, dropping messages")

    def _build_detection_message(self, pred: Dict, frame: VideoFrame) -> Dict:
        """
        Build detection message for MQTT publishing.

        Args:
            pred: Predictions dict from on_video_frame
            frame: Video frame

        Returns:
            Detection message dict
        """
        detections = pred["detections"]

        # Convert detections to list of dicts
        detection_list = []
        for i in range(len(detections)):
            detection_list.append({
                "bbox": detections.xyxy[i].tolist(),
                "confidence": float(detections.confidence[i]),
                "class_id": int(detections.class_id[i]),
                "tracker_id": int(detections.tracker_id[i]) if detections.tracker_id is not None else None,
            })

        return {
            "service_id": self.config.service_id,
            "frame_id": pred["frame_id"],
            "timestamp": pred["timestamp"],
            "detections": detection_list,
        }

    def _build_zone_event_message(self, pred: Dict, frame: VideoFrame) -> Dict:
        """
        Build zone event message for MQTT publishing.

        Args:
            pred: Predictions dict from on_video_frame
            frame: Video frame

        Returns:
            Zone event message dict
        """
        return {
            "service_id": self.config.service_id,
            "frame_id": pred["frame_id"],
            "timestamp": pred["timestamp"],
            "zone_counts": pred["zone_counts"],
        }

    def _publish_loop(self):
        """
        MQTT publisher thread loop.

        This thread continuously reads messages from the publish queue
        and publishes them to MQTT.

        Thread: MQTT Publisher Thread (our thread)
        """
        logger.info("MQTT publisher loop started")

        while not self.stop_event.is_set():
            try:
                msg_type, msg = self.publish_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                if msg_type == "detection":
                    self.detection_publisher.publish_detection(msg)
                elif msg_type == "zone_event":
                    self.zone_event_publisher.publish_zone_event(msg)
            except Exception as e:
                logger.error(f"Error publishing {msg_type}: {e}", exc_info=True)

        logger.info("MQTT publisher loop stopped")

    # ─────────────────────────────────────────────────────────────────────
    # Command Handlers (called by Control Plane Thread)
    # ─────────────────────────────────────────────────────────────────────

    def _handle_add_zone(self, command: Dict):
        """Handle add_zone command (Control Plane Thread)."""
        zone_id = command["zone_id"]
        zone_type = command["zone_type"]
        coordinates = [tuple(c) for c in command["coordinates"]]

        zone_config = ZoneConfig(
            zone_id=zone_id,
            zone_type=zone_type,
            coordinates=coordinates,
            enabled=True
        )

        zone = self._create_zone_from_config(zone_config)
        self.zone_registry.add_zone(zone_id, zone)

        self.control_plane.publish_status("zone_added", {"zone_id": zone_id})
        logger.info(f"Zone added: {zone_id}")

    def _handle_remove_zone(self, command: Dict):
        """Handle remove_zone command (Control Plane Thread)."""
        zone_id = command["zone_id"]
        self.zone_registry.remove_zone(zone_id)

        self.control_plane.publish_status("zone_removed", {"zone_id": zone_id})
        logger.info(f"Zone removed: {zone_id}")

    def _handle_enable_zone(self, command: Dict):
        """Handle enable_zone command (Control Plane Thread)."""
        zone_id = command["zone_id"]
        self.zone_registry.enable_zone(zone_id)

        self.control_plane.publish_status("zone_enabled", {"zone_id": zone_id})
        logger.info(f"Zone enabled: {zone_id}")

    def _handle_disable_zone(self, command: Dict):
        """Handle disable_zone command (Control Plane Thread)."""
        zone_id = command["zone_id"]
        self.zone_registry.disable_zone(zone_id)

        self.control_plane.publish_status("zone_disabled", {"zone_id": zone_id})
        logger.info(f"Zone disabled: {zone_id}")

    def _handle_list_zones(self, command: Dict):
        """Handle list_zones command (Control Plane Thread)."""
        zones = self.zone_registry.list_zones()

        self.control_plane.publish_status("zones_list", {"zones": zones})
        logger.info(f"Listed zones: {list(zones.keys())}")

    def _handle_set_model(self, command: Dict):
        """
        Handle set_model command (Control Plane Thread).

        Hot-swap model without recreating pipeline.
        """
        variant = command["variant"]
        input_size = command.get("input_size", 640)

        # Load new model
        new_model = self.model_loader.load_model(
            variant=variant,
            input_size=input_size
        )

        # Atomic swap (thread-safe)
        with self._model_lock:
            old_model = self.model
            self.model = new_model

        # Cleanup old model (outside lock)
        del old_model

        # Publish status
        model_info = self.model_loader.get_current_model_info()
        self.control_plane.publish_status("model_changed", model_info)
        logger.info(f"Model changed: {model_info}")

    def _handle_get_model(self, command: Dict):
        """Handle get_model command (Control Plane Thread)."""
        model_info = self.model_loader.get_current_model_info()

        self.control_plane.publish_status("model_info", model_info)
        logger.info(f"Current model: {model_info}")
