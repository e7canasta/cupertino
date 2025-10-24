"""
Zone Monitor Demo
=================

Demonstrates cupertino_zone package usage with NEW REFACTORED API.

Example: Monitor vehicles in a polygon zone and line crossing.

Architecture:
- geometry: PolygonZone, LineZone (immutable shapes)
- analytics: ZoneCounter, CrossingTracker (stateful counting)
- rendering: ZoneVisualizer (drawing)
- pipeline: Orchestration
"""

import supervision as sv
import numpy as np
from ultralytics import YOLO

# New API - separation of concerns
from cupertino_zone import (
    PolygonZone,
    LineZone,
    ZoneVisualizer,
    PipelineBuilder,
)

VIDEO_PATH = "./data/videos/vehicles-1280x720.mp4"


def main():
    """Run zone monitoring on vehicles video using NEW API."""

    # 1. Load detection model
    model = YOLO("yolov8n.pt")

    # 2. Get video info for zone setup
    video_info = sv.VideoInfo.from_video_path(VIDEO_PATH)
    width, height = video_info.width, video_info.height

    # 3. Define zones (NEW API - pure geometry)
    # Polygon zone - monitor area in bottom half of frame
    polygon_zone = PolygonZone(
        vertices=np.array([
            [width // 4, height // 2],
            [3 * width // 4, height // 2],
            [3 * width // 4, height - 50],
            [width // 4, height - 50],
        ], dtype=np.int32),  # Note: int32 for cv2 compatibility
        frame_resolution_wh=(width, height),
    )

    # Line zone - count crossings at middle of frame
    line_zone = LineZone(
        start=(0, height // 2),
        end=(width, height // 2),
    )

    # 4. Create visualizer with custom colors
    visualizer = ZoneVisualizer(
        zone_color=sv.Color(r=0, g=255, b=0),  # Green zones
        text_color=sv.Color(r=255, g=255, b=255),  # White text
        thickness=3,
        text_scale=0.8,
        opacity=0.2,
    )

    # 5. Build pipeline using Builder pattern (NEW API)
    pipeline = (
        PipelineBuilder()
        .with_video(VIDEO_PATH)
        .with_model(model)
        .add_polygon_zone("parking_area", polygon_zone)  # Type-safe methods
        .add_line_zone("crossing", line_zone)
        .with_visualizer(visualizer)
        .with_stride(2)  # Process every 2nd frame
        .with_output_fps(10)
        .build()
    )

    # 6. Process video
    print("🎬 Starting zone monitoring...")
    print(f"  Video: {VIDEO_PATH}")
    print(f"  Zones: 1 polygon + 1 line")
    print()

    output_path = pipeline.process()

    # 7. Print final statistics (access via pipeline config)
    print()
    print("✓ Zone monitoring completed!")
    print(f"  Output: {output_path}")
    
    # Get final stats from pipeline zones
    for zone_cfg in pipeline.config.zones:
        stats = zone_cfg.counter.get_stats()
        print(f"  {zone_cfg.zone_id}: {stats}")


if __name__ == "__main__":
    main()
