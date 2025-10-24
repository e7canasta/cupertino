"""
Zone Monitor Pipeline Module
=============================

Bounded Context: Video processing orchestration.

Design:
- Orchestrator: Combina detection, tracking, zones, visualization
- Builder pattern: Configuración fluida
- Fail Fast: Validación en construcción, no en runtime

Dependencies:
- supervision (video utils, ByteTrack)
- ultralytics (YOLO - opcional, inyectable)
"""

import supervision as sv
import numpy as np
from pathlib import Path
from typing import Callable, Any
from dataclasses import dataclass

from cupertino_zone.zone import PolygonZoneMonitor, LineZoneMonitor
from cupertino_zone.counter import ZoneCounter
from cupertino_zone.visualizer import ZoneVisualizer
from utils import get_target_run_folder


@dataclass
class PipelineConfig:
    """Pipeline configuration (immutable)."""

    video_path: str
    output_folder: str
    model: Any  # YOLO model or detector
    tracker: sv.ByteTrack
    zones: list[PolygonZoneMonitor | LineZoneMonitor]
    visualizer: ZoneVisualizer
    stride: int = 1
    output_fps: int = 5


class ZoneMonitorPipeline:
    """
    Orchestrates zone monitoring video processing.

    Design:
    - Builder pattern for construction
    - Single Responsibility: solo orquesta, delega cálculos
    - Fail Fast: valida configuración antes de procesar
    """

    def __init__(self, config: PipelineConfig):
        """
        Args:
            config: Pipeline configuration
        """
        self.config = config
        self._validate_config()

        # Initialize counters for each zone
        self.counters = [ZoneCounter() for _ in config.zones]

    def _validate_config(self) -> None:
        """Validate configuration (fail fast)."""
        video_path = Path(self.config.video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {self.config.video_path}")

        if len(self.config.zones) == 0:
            raise ValueError("At least one zone is required")

    def process(self) -> str:
        """
        Process video and return output path.

        Returns:
            Path to output video
        """
        # Setup video I/O
        video_info = sv.VideoInfo.from_video_path(self.config.video_path)
        frames_generator = sv.get_video_frames_generator(
            self.config.video_path,
            stride=self.config.stride
        )

        # Adjust output FPS
        video_info.fps = self.config.output_fps

        # Create output path
        output_path = f"{self.config.output_folder}/zone_monitor_output.mp4"

        # Process frames
        with sv.VideoSink(output_path, video_info) as sink:
            for frame_idx, frame in enumerate(frames_generator):
                annotated_frame = self._process_frame(frame, frame_idx)
                sink.write_frame(annotated_frame)

        print(f"✓ Zone monitoring completed. Output: {output_path}")
        return output_path

    def _process_frame(self, frame: np.ndarray, frame_idx: int) -> np.ndarray:
        """
        Process a single frame.

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

        # 3. Process each zone
        annotated_frame = frame.copy()
        for zone, counter in zip(self.config.zones, self.counters):
            if isinstance(zone, PolygonZoneMonitor):
                annotated_frame = self._process_polygon_zone(
                    annotated_frame, zone, counter, detections
                )
            elif isinstance(zone, LineZoneMonitor):
                annotated_frame = self._process_line_zone(
                    annotated_frame, zone, detections
                )

        return annotated_frame

    def _process_polygon_zone(
        self,
        frame: np.ndarray,
        zone: PolygonZoneMonitor,
        counter: ZoneCounter,
        detections: sv.Detections,
    ) -> np.ndarray:
        """Process polygon zone on frame."""
        # Check which detections are in zone
        in_zone_mask = zone.trigger(detections)

        # Update counter
        counter.update(detections, in_zone_mask)
        stats = counter.get_stats()

        # Visualize
        frame = self.config.visualizer.draw_polygon_zone(frame, zone, stats)
        frame = self.config.visualizer.draw_detections_in_zone(frame, detections, in_zone_mask)

        return frame

    def _process_line_zone(
        self,
        frame: np.ndarray,
        zone: LineZoneMonitor,
        detections: sv.Detections,
    ) -> np.ndarray:
        """Process line zone on frame."""
        # Check for crossings
        zone.trigger(detections)

        # Visualize
        frame = self.config.visualizer.draw_line_zone(frame, zone, display_counts=True)

        return frame


class PipelineBuilder:
    """
    Builder for ZoneMonitorPipeline.

    Design: Fluent API for construction, fail-fast validation.
    """

    def __init__(self):
        self._video_path: str | None = None
        self._output_folder: str | None = None
        self._model: Any = None
        self._tracker: sv.ByteTrack | None = None
        self._zones: list[PolygonZoneMonitor | LineZoneMonitor] = []
        self._visualizer: ZoneVisualizer | None = None
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
        """Set detection model."""
        self._model = model
        return self

    def with_tracker(self, tracker: sv.ByteTrack) -> "PipelineBuilder":
        """Set object tracker."""
        self._tracker = tracker
        return self

    def add_zone(self, zone: PolygonZoneMonitor | LineZoneMonitor) -> "PipelineBuilder":
        """Add a zone to monitor."""
        self._zones.append(zone)
        return self

    def with_visualizer(self, visualizer: ZoneVisualizer) -> "PipelineBuilder":
        """Set visualizer."""
        self._visualizer = visualizer
        return self

    def with_stride(self, stride: int) -> "PipelineBuilder":
        """Set frame stride."""
        self._stride = stride
        return self

    def with_output_fps(self, fps: int) -> "PipelineBuilder":
        """Set output FPS."""
        self._output_fps = fps
        return self

    def build(self) -> ZoneMonitorPipeline:
        """
        Build the pipeline.

        Raises:
            ValueError: If required configuration is missing
        """
        if self._video_path is None:
            raise ValueError("Video path is required")
        if self._model is None:
            raise ValueError("Detection model is required")

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
            stride=self._stride,
            output_fps=self._output_fps,
        )

        return ZoneMonitorPipeline(config)
