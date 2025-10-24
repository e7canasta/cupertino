"""
Configuration schema for StreamProcessor service.

This module defines the configuration structure for the stream processor,
including RTSP settings, model configuration, zone definitions, and MQTT
publishing settings.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional
import yaml


@dataclass(frozen=True)
class ModelConfig:
    """
    YOLO model configuration with catalog support.
    
    Supported models (based on available files in models/):
    - YOLO11: n, s, m, l, x (320, 640 for ONNX | any for PT)
    - YOLO12: n, s, m, l, x (320, 640 for ONNX | any for PT)
    
    Formats:
    - ONNX: Pre-exported optimized models (yolo{version}{variant}-{size}.onnx)
    - PT: PyTorch native models (yolo{version}{variant}.pt)
    """

    model_version: str = "12"  # "11" or "12"
    model_variant: str = "n"  # n, s, m, l, x
    input_size: int = 640
    model_format: str = "onnx"  # "onnx" or "pt"
    confidence: float = 0.5
    iou_threshold: float = 0.5
    max_detections: int = 300

    def __post_init__(self):
        """Validate model configuration."""
        valid_versions = {"11", "12"}
        if self.model_version not in valid_versions:
            raise ValueError(
                f"Invalid model_version: {self.model_version}. "
                f"Must be one of {valid_versions}"
            )

        valid_variants = {"n", "s", "m", "l", "x"}
        if self.model_variant not in valid_variants:
            raise ValueError(
                f"Invalid model_variant: {self.model_variant}. "
                f"Must be one of {valid_variants}"
            )

        valid_formats = {"onnx", "pt"}
        if self.model_format not in valid_formats:
            raise ValueError(
                f"Invalid model_format: {self.model_format}. "
                f"Must be one of {valid_formats}"
            )

        # ONNX models have fixed input sizes
        if self.model_format == "onnx":
            valid_sizes = {320, 640}
            if self.input_size not in valid_sizes:
                raise ValueError(
                    f"Invalid input_size for ONNX: {self.input_size}. "
                    f"Must be one of {valid_sizes}"
                )
        # PT models can accept any reasonable size
        else:  # pt
            if not 32 <= self.input_size <= 1280:
                raise ValueError(
                    f"input_size must be in [32, 1280], got {self.input_size}"
                )

        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0.0, 1.0], got {self.confidence}"
            )

        if not 0.0 <= self.iou_threshold <= 1.0:
            raise ValueError(
                f"iou_threshold must be in [0.0, 1.0], got {self.iou_threshold}"
            )

    def get_model_filename(self) -> str:
        """
        Get the model filename based on configuration.
        
        Returns:
            str: Model filename (e.g., "yolo12n-640.onnx" or "yolo12n.pt")
        """
        if self.model_format == "onnx":
            return f"yolo{self.model_version}{self.model_variant}-{self.input_size}.onnx"
        else:  # pt
            return f"yolo{self.model_version}{self.model_variant}.pt"


@dataclass(frozen=True)
class ZoneConfig:
    """Zone configuration (polygon or line)."""

    zone_id: str
    zone_type: str  # "polygon" or "line"
    coordinates: List[Tuple[int, int]]
    enabled: bool = True

    def __post_init__(self):
        """Validate zone configuration."""
        if self.zone_type == "polygon":
            if len(self.coordinates) < 3:
                raise ValueError(
                    f"Polygon zone '{self.zone_id}' must have at least 3 points, "
                    f"got {len(self.coordinates)}"
                )
        elif self.zone_type == "line":
            if len(self.coordinates) != 2:
                raise ValueError(
                    f"Line zone '{self.zone_id}' must have exactly 2 points, "
                    f"got {len(self.coordinates)}"
                )
        else:
            raise ValueError(
                f"Invalid zone_type: {self.zone_type}. "
                f"Must be 'polygon' or 'line'"
            )


@dataclass(frozen=True)
class MQTTConfig:
    """MQTT broker configuration."""

    broker: str
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    qos: int = 0  # Data plane QoS (fire-and-forget)

    detection_topic: str = "cupertino/data/detections/{service_id}"
    zone_event_topic: str = "cupertino/data/zones/{service_id}"

    def __post_init__(self):
        """Validate MQTT configuration."""
        if not 1 <= self.port <= 65535:
            raise ValueError(
                f"MQTT port must be in [1, 65535], got {self.port}"
            )

        if self.qos not in {0, 1, 2}:
            raise ValueError(
                f"MQTT QoS must be 0, 1, or 2, got {self.qos}"
            )


@dataclass(frozen=True)
class ProcessorConfig:
    """
    Main configuration for StreamProcessor service.

    This configuration is loaded from YAML and validated at startup.
    Immutable after construction (frozen dataclass).
    """

    # Service identification
    service_id: str

    # RTSP stream configuration
    rtsp_url: str
    max_fps: int = 25
    frame_resolution_wh: Tuple[int, int] = (1280, 720)  # (width, height)

    # Model configuration
    model_config: ModelConfig = field(default_factory=ModelConfig)
    models_dir: Path = Path("./models")

    # Zone configuration
    zones: List[ZoneConfig] = field(default_factory=list)

    # MQTT configuration
    mqtt_config: MQTTConfig = field(default_factory=MQTTConfig)

    def __post_init__(self):
        """Validate processor configuration."""
        # Validate service_id
        if not self.service_id:
            raise ValueError("service_id cannot be empty")

        # Validate RTSP URL
        if not self.rtsp_url:
            raise ValueError("rtsp_url cannot be empty")

        # Validate max_fps
        if not 1 <= self.max_fps <= 60:
            raise ValueError(
                f"max_fps must be in [1, 60], got {self.max_fps}"
            )

        # Validate frame_resolution_wh
        width, height = self.frame_resolution_wh
        if width <= 0 or height <= 0:
            raise ValueError(
                f"frame_resolution_wh must have positive dimensions, got {self.frame_resolution_wh}"
            )
        if width > 4096 or height > 4096:
            raise ValueError(
                f"frame_resolution_wh dimensions too large (max 4096x4096), got {self.frame_resolution_wh}"
            )

        # Validate models_dir exists
        if not self.models_dir.exists():
            raise FileNotFoundError(
                f"Models directory not found: {self.models_dir}\n"
                f"Create directory or update 'models_dir' in config"
            )

        if not self.models_dir.is_dir():
            raise ValueError(
                f"models_dir must be a directory, got file: {self.models_dir}"
            )

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> "ProcessorConfig":
        """
        Load configuration from YAML file.

        Example YAML:
            service_id: "cam_01"
            rtsp_url: "rtsp://localhost:8554/camera1"
            max_fps: 25
            frame_resolution_wh: [1280, 720]  # [width, height]

            model_config:
              model_variant: "n"
              input_size: 640
              confidence: 0.5

            models_dir: "./models"

            zones:
              - zone_id: "entrance"
                zone_type: "polygon"
                coordinates: [[100, 200], [500, 200], [500, 600], [100, 600]]
                enabled: true

            mqtt_config:
              broker: "localhost"
              port: 1883
              username: null
              password: null
        """
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Parse nested configs
        model_config_data = data.get("model_config", {})
        model_config = ModelConfig(**model_config_data)

        mqtt_config_data = data.get("mqtt_config", {})
        mqtt_config = MQTTConfig(**mqtt_config_data)

        zones_data = data.get("zones", [])
        zones = [
            ZoneConfig(
                zone_id=z["zone_id"],
                zone_type=z["zone_type"],
                coordinates=[tuple(coord) for coord in z["coordinates"]],
                enabled=z.get("enabled", True)
            )
            for z in zones_data
        ]

        # Parse models_dir as Path
        models_dir = Path(data.get("models_dir", "./models"))

        # Parse frame_resolution_wh
        frame_resolution_data = data.get("frame_resolution_wh", [1280, 720])
        frame_resolution_wh = tuple(frame_resolution_data)

        return cls(
            service_id=data["service_id"],
            rtsp_url=data["rtsp_url"],
            max_fps=data.get("max_fps", 25),
            frame_resolution_wh=frame_resolution_wh,
            model_config=model_config,
            models_dir=models_dir,
            zones=zones,
            mqtt_config=mqtt_config,
        )
