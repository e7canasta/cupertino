"""
Zone Monitor Demo
=================

Demonstrates cupertino_zone package usage.

Example: Monitor vehicles in a polygon zone.
"""

import supervision as sv
import numpy as np
from ultralytics import YOLO

from cupertino_zone import (
    PolygonZoneMonitor,
    LineZoneMonitor,
    ZoneVisualizer,
    PipelineBuilder,
)

VIDEO_PATH = "./data/videos/vehicles-1280x720.mp4"


def main():
    """Run zone monitoring on vehicles video."""

    # 1. Load detection model
    model = YOLO("yolov8n.pt")

    # 2. Get video info for zone setup
    video_info = sv.VideoInfo.from_video_path(VIDEO_PATH)
    width, height = video_info.width, video_info.height

    # 3. Define zones
    # Polygon zone - monitor area in bottom half of frame
    polygon_zone = PolygonZoneMonitor(
        polygon=np.array([
            [width // 4, height // 2],
            [3 * width // 4, height // 2],
            [3 * width // 4, height - 50],
            [width // 4, height - 50],
        ], dtype=np.int64),
        frame_resolution_wh=(width, height),
    )

    # Line zone - count crossings at middle of frame
    line_zone = LineZoneMonitor(
        start=sv.Point(x=0, y=height // 2),
        end=sv.Point(x=width, y=height // 2),
    )

    # 4. Create visualizer with custom colors
    visualizer = ZoneVisualizer(
        zone_color=sv.Color(r=0, g=255, b=0),  # Green zones
        text_color=sv.Color(r=255, g=255, b=255),  # White text
        thickness=3,
        text_scale=0.8,
        opacity=0.2,
    )

    # 5. Build pipeline using Builder pattern
    pipeline = (
        PipelineBuilder()
        .with_video(VIDEO_PATH)
        .with_model(model)
        .add_zone(polygon_zone)
        .add_zone(line_zone)
        .with_visualizer(visualizer)
        .with_stride(2)  # Process every 2nd frame
        .with_output_fps(10)
        .build()
    )

    # 6. Process video
    output_path = pipeline.process()

    print(f"✓ Zone monitoring completed!")
    print(f"  Output: {output_path}")
    print(f"  Polygon zone final count: {polygon_zone.current_count}")
    print(f"  Line zone crossings - IN: {line_zone.in_count}, OUT: {line_zone.out_count}")


if __name__ == "__main__":
    main()
