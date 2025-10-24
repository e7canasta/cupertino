"""
Zone Monitor Pipeline Module
=============================

Bounded Context: Video processing orchestration for zone monitoring.

Design (Refactored):
- Orchestrator: Combines detection, tracking, zones, analytics, visualization
- Builder pattern: Fluent configuration
- Fail Fast: Validation at build time, not runtime
- Uses new architecture: geometry + analytics + rendering

Dependencies:
- supervision (video utils, ByteTrack)
- ultralytics (YOLO - optional, injectable)
- cupertino_zone.geometry (zone shapes)
- cupertino_zone.analytics (counters, trackers)
- cupertino_zone.rendering (visualizers)
"""

import supervision as sv
import numpy as np
from pathlib import Path
from typing import Any
from dataclasses import dataclass

from cupertino_zone.geometry.shapes import PolygonZone, LineZone
from cupertino_zone.geometry.detector import ZoneDetector
from cupertino_zone.analytics.counter import ZoneCounter, ZoneStats
from cupertino_zone.analytics.tracker import CrossingTracker
from cupertino_zone.rendering.visualizer import ZoneVisualizer
from utils import get_target_run_folder


@dataclass
class ZoneConfig:
    """
    Configuration for a single zone.

    Design:
    - Tagged union pattern (type + zone)
    - Encapsulates zone + counter + tracker (if line)
    """

    zone_id: str
    zone: PolygonZone | LineZone
    counter: ZoneCounter
    tracker: CrossingTracker | None = None  # Only for LineZone


@dataclass
class PipelineConfig:
    """
    Pipeline configuration (immutable).

    Design:
    - All dependencies injected
    - Validated at construction
    - Immutable after build
    """

    video_path: str
    output_folder: str
    model: Any  # YOLO model or detector
    tracker: sv.ByteTrack
    zones: list[ZoneConfig]
    visualizer: ZoneVisualizer
    class_names: dict[int, str] | None = None
    stride: int = 1
    output_fps: int = 5


class ZoneMonitorPipeline:
    """
    Orchestrates zone monitoring video processing.

    Design (Refactored):
    - Uses new geometry/analytics/rendering architecture
    - Single Responsibility: orchestration only
    - Delegates computation to specialized modules
    - Fail Fast: validates configuration before processing

    Usage:
        pipeline = (
            PipelineBuilder()
            .with_video("video.mp4")
            .with_model(model)
            .add_polygon_zone("entrance", polygon)
            .add_line_zone("crossing", line)
            .build()
        )

        output_path = pipeline.process()
    """

    def __init__(self, config: PipelineConfig):
        """
        Initialize pipeline with configuration.

        Args:
            config: Pipeline configuration (validated)
        """
        self.config = config
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration (fail fast)."""
        video_path = Path(self.config.video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {self.config.video_path}")

        if len(self.config.zones) == 0:
            raise ValueError("At least one zone is required")

        # Validate line zones have trackers
        for zone_cfg in self.config.zones:
            if isinstance(zone_cfg.zone, LineZone) and zone_cfg.tracker is None:
                raise ValueError(f"Line zone '{zone_cfg.zone_id}' requires a CrossingTracker")

    def process(self) -> str:
        """
        Process video and return output path.

        Returns:
            Path to output video

        Raises:
            FileNotFoundError: If video not found
            RuntimeError: If processing fails
        """
        # Setup video I/O
        video_info = sv.VideoInfo.from_video_path(self.config.video_path)
        frames_generator = sv.get_video_frames_generator(
            self.config.video_path, stride=self.config.stride
        )

        # Adjust output FPS
        video_info.fps = self.config.output_fps

        # Create output path
        output_path = f"{self.config.output_folder}/zone_monitor_output.mp4"
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Process frames
        with sv.VideoSink(output_path, video_info) as sink:
            for frame_idx, frame in enumerate(frames_generator):
                annotated_frame = self._process_frame(frame, frame_idx)
                sink.write_frame(annotated_frame)

        print(f"✓ Zone monitoring completed. Output: {output_path}")
        return output_path

    def _process_frame(self, frame: np.ndarray, frame_idx: int) -> np.ndarray:
        """
        Process a single frame through the pipeline.

        Pipeline stages:
        1. Detection (YOLO)
        2. Tracking (ByteTrack)
        3. Zone detection (geometry layer)
        4. Analytics update (counters)
        5. Visualization (rendering layer)

        Args:
            frame: Input frame
            frame_idx: Frame index

        Returns:
            Annotated frame
        """
        # 1. Run detection
        results = self.config.model(frame)[0]
        detections = sv.Detections.from_ultralytics(results)

        # 2. Track objects
        detections = self.config.tracker.update_with_detections(detections)

        # 3-5. Process each zone
        annotated_frame = frame.copy()
        for zone_cfg in self.config.zones:
            if isinstance(zone_cfg.zone, PolygonZone):
                annotated_frame = self._process_polygon_zone(
                    annotated_frame, zone_cfg, detections
                )
            elif isinstance(zone_cfg.zone, LineZone):
                annotated_frame = self._process_line_zone(
                    annotated_frame, zone_cfg, detections
                )

        return annotated_frame

    def _process_polygon_zone(
        self,
        frame: np.ndarray,
        zone_cfg: ZoneConfig,
        detections: sv.Detections,
    ) -> np.ndarray:
        """
        Process polygon zone on frame.

        Args:
            frame: Frame to annotate
            zone_cfg: Zone configuration
            detections: All detections

        Returns:
            Annotated frame
        """
        # Detect which objects are in zone
        in_zone_mask = ZoneDetector.detect_polygon(zone_cfg.zone, detections)

        # Update counter
        zone_cfg.counter.update_polygon(in_zone_mask, detections, self.config.class_names)
        stats = zone_cfg.counter.get_stats()

        # Visualize
        frame = self.config.visualizer.draw_polygon(frame, zone_cfg.zone, stats)
        frame = self.config.visualizer.draw_detections_in_zone(
            frame, detections, in_zone_mask
        )

        return frame

    def _process_line_zone(
        self,
        frame: np.ndarray,
        zone_cfg: ZoneConfig,
        detections: sv.Detections,
    ) -> np.ndarray:
        """
        Process line zone on frame.

        Args:
            frame: Frame to annotate
            zone_cfg: Zone configuration (must have tracker)
            detections: All detections (must have tracker_id)

        Returns:
            Annotated frame
        """
        if zone_cfg.tracker is None:
            raise ValueError(f"Line zone '{zone_cfg.zone_id}' requires a tracker")

        # Detect crossings (stateless, with injected state)
        crossed_in, crossed_out, new_state = ZoneDetector.detect_line_crossing(
            zone_cfg.zone, detections, zone_cfg.tracker.state
        )

        # Update tracker state
        zone_cfg.tracker.state = new_state

        # Update counter
        zone_cfg.counter.update_line(
            crossed_in, crossed_out, detections, self.config.class_names
        )
        stats = zone_cfg.counter.get_stats()

        # Visualize
        frame = self.config.visualizer.draw_line(frame, zone_cfg.zone, stats)

        return frame


class PipelineBuilder:
    """
    Builder for ZoneMonitorPipeline.

    Design:
    - Fluent API for construction
    - Fail-fast validation
    - Sensible defaults
    - Type-safe zone creation

    Usage:
        builder = PipelineBuilder()
        pipeline = (
            builder
            .with_video("video.mp4")
            .with_model(yolo_model)
            .add_polygon_zone("entrance", polygon_zone)
            .add_line_zone("crossing", line_zone)
            .build()
        )
    """

    def __init__(self):
        self._video_path: str | None = None
        self._output_folder: str | None = None
        self._model: Any = None
        self._tracker: sv.ByteTrack | None = None
        self._zones: list[ZoneConfig] = []
        self._visualizer: ZoneVisualizer | None = None
        self._class_names: dict[int, str] | None = None
        self._stride: int = 1
        self._output_fps: int = 5

    def with_video(self, video_path: str) -> "PipelineBuilder":
        """Set input video path."""
        self._video_path = video_path
        return self

    def with_output_folder(self, folder: str) -> "PipelineBuilder":
        """Set output folder."""
        self._output_folder = folder
        return self

    def with_model(self, model: Any) -> "PipelineBuilder":
        """Set detection model (e.g., YOLO)."""
        self._model = model
        return self

    def with_tracker(self, tracker: sv.ByteTrack) -> "PipelineBuilder":
        """Set object tracker."""
        self._tracker = tracker
        return self

    def with_class_names(self, class_names: dict[int, str]) -> "PipelineBuilder":
        """Set class ID to name mapping."""
        self._class_names = class_names
        return self

    def with_visualizer(self, visualizer: ZoneVisualizer) -> "PipelineBuilder":
        """Set visualizer."""
        self._visualizer = visualizer
        return self

    def with_stride(self, stride: int) -> "PipelineBuilder":
        """Set frame stride (process every N frames)."""
        self._stride = stride
        return self

    def with_output_fps(self, fps: int) -> "PipelineBuilder":
        """Set output video FPS."""
        self._output_fps = fps
        return self

    def add_polygon_zone(
        self, zone_id: str, zone: PolygonZone
    ) -> "PipelineBuilder":
        """
        Add a polygon zone for presence detection.

        Args:
            zone_id: Unique identifier for this zone
            zone: Polygon geometry

        Returns:
            Self for chaining
        """
        zone_cfg = ZoneConfig(
            zone_id=zone_id,
            zone=zone,
            counter=ZoneCounter(zone_id=zone_id),
            tracker=None,  # Polygon zones don't need crossing tracker
        )
        self._zones.append(zone_cfg)
        return self

    def add_line_zone(self, zone_id: str, zone: LineZone) -> "PipelineBuilder":
        """
        Add a line zone for crossing detection.

        Args:
            zone_id: Unique identifier for this zone
            zone: Line geometry

        Returns:
            Self for chaining
        """
        zone_cfg = ZoneConfig(
            zone_id=zone_id,
            zone=zone,
            counter=ZoneCounter(zone_id=zone_id),
            tracker=CrossingTracker(),  # Line zones need crossing tracker
        )
        self._zones.append(zone_cfg)
        return self

    def build(self) -> ZoneMonitorPipeline:
        """
        Build the pipeline.

        Returns:
            Configured pipeline

        Raises:
            ValueError: If required configuration is missing
        """
        if self._video_path is None:
            raise ValueError("Video path is required (use .with_video())")
        if self._model is None:
            raise ValueError("Detection model is required (use .with_model())")

        # Defaults
        if self._output_folder is None:
            self._output_folder = get_target_run_folder(application_name="zone_monitor")
        if self._tracker is None:
            self._tracker = sv.ByteTrack()
        if self._visualizer is None:
            self._visualizer = ZoneVisualizer()

        config = PipelineConfig(
            video_path=self._video_path,
            output_folder=self._output_folder,
            model=self._model,
            tracker=self._tracker,
            zones=self._zones,
            visualizer=self._visualizer,
            class_names=self._class_names,
            stride=self._stride,
            output_fps=self._output_fps,
        )

        return ZoneMonitorPipeline(config)
