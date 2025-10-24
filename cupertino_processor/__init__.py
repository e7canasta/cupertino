"""
cupertino_processor - Stream Processing Service for Zone Monitoring

This package provides the main inference pipeline service that processes
RTSP video streams, performs YOLO object detection, monitors zones, and
publishes results via MQTT.

Architecture:
- StreamProcessorService: Main orchestrator
- ZoneMonitorRegistry: Thread-safe zone management
- ModelLoader: YOLO model loading and caching
- ProcessorConfig: Configuration management

Threading Model:
- Video Source Thread (InferencePipeline internal)
- Inference Thread (InferencePipeline internal, calls on_video_frame)
- Dispatch Thread (InferencePipeline internal, calls on_prediction)
- MQTT Publisher Thread (our thread for publishing)
- Control Plane Thread (paho-mqtt internal for commands)
"""

from cupertino_processor.config import ProcessorConfig
from cupertino_processor.registry import ZoneMonitorRegistry
from cupertino_processor.model_loader import ModelLoader
from cupertino_processor.service import StreamProcessorService

__all__ = [
    "ProcessorConfig",
    "ZoneMonitorRegistry",
    "ModelLoader",
    "StreamProcessorService",
]
