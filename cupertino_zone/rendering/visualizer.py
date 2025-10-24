"""
Zone Visualizer Module
======================

Pure visualization layer for zones and statistics.

Design:
- Stateless rendering (pure functions)
- No business logic
- Configurable styles
- Uses supervision drawing utilities

Dependencies:
- supervision (draw utilities, Color, Point)
- numpy (arrays)
"""

import numpy as np
import supervision as sv
from typing import Tuple

from cupertino_zone.geometry.shapes import PolygonZone, LineZone
from cupertino_zone.analytics.counter import ZoneStats


class ZoneVisualizer:
    """
    Stateless visualizer for zone rendering.

    Design Philosophy:
    - SRP: Only draws, doesn't compute
    - Configurable styles
    - Works with new geometry primitives
    - No coupling to monitors (legacy removed)

    Usage:
        visualizer = ZoneVisualizer(
            zone_color=sv.Color.GREEN,
            text_color=sv.Color.WHITE,
            thickness=2
        )

        # Draw polygon zone
        frame = visualizer.draw_polygon(frame, polygon_zone, stats)

        # Draw line zone
        frame = visualizer.draw_line(frame, line_zone, stats)

        # Highlight detections
        frame = visualizer.draw_detections_in_zone(frame, detections, mask)
    """

    def __init__(
        self,
        zone_color: sv.Color = sv.Color(r=0, g=255, b=0),
        text_color: sv.Color = sv.Color(r=255, g=255, b=255),
        text_background_color: sv.Color = sv.Color(r=0, g=0, b=0),
        thickness: int = 2,
        text_scale: float = 0.6,
        text_thickness: int = 2,
        text_padding: int = 10,
        opacity: float = 0.3,
    ):
        """
        Initialize visualizer with style configuration.

        Args:
            zone_color: Color for zone outline/fill
            text_color: Color for text labels
            text_background_color: Background color for text
            thickness: Line thickness for drawing
            text_scale: Scale factor for text
            text_thickness: Thickness for text
            text_padding: Padding for text background
            opacity: Opacity for zone fill (0-1)
        """
        self.zone_color = zone_color
        self.text_color = text_color
        self.text_background_color = text_background_color
        self.thickness = thickness
        self.text_scale = text_scale
        self.text_thickness = text_thickness
        self.text_padding = text_padding
        self.opacity = opacity

    def draw_polygon(
        self,
        frame: np.ndarray,
        zone: PolygonZone,
        stats: ZoneStats | None = None,
    ) -> np.ndarray:
        """
        Draw a polygon zone on the frame.

        Args:
            frame: Video frame to draw on
            zone: Polygon geometry
            stats: Optional statistics to display

        Returns:
            Frame with polygon drawn
        """
        # Draw filled polygon (with opacity)
        frame = sv.draw_filled_polygon(
            scene=frame,
            polygon=zone.vertices,
            color=self.zone_color,
            opacity=self.opacity,
        )

        # Draw polygon outline
        frame = sv.draw_polygon(
            scene=frame,
            polygon=zone.vertices,
            color=self.zone_color,
            thickness=self.thickness,
        )

        # Draw stats text if provided
        if stats is not None:
            # Position text at top-left of polygon bounding box
            min_x = int(np.min(zone.vertices[:, 0]))
            min_y = int(np.min(zone.vertices[:, 1]))
            text_anchor = sv.Point(x=min_x, y=max(min_y - 10, 20))

            frame = sv.draw_text(
                scene=frame,
                text=str(stats),
                text_anchor=text_anchor,
                text_color=self.text_color,
                text_scale=self.text_scale,
                text_thickness=self.text_thickness,
                text_padding=self.text_padding,
                background_color=self.text_background_color,
            )

        return frame

    def draw_line(
        self,
        frame: np.ndarray,
        zone: LineZone,
        stats: ZoneStats | None = None,
    ) -> np.ndarray:
        """
        Draw a line zone on the frame.

        Args:
            frame: Video frame to draw on
            zone: Line geometry
            stats: Optional statistics to display (IN/OUT counts)

        Returns:
            Frame with line drawn
        """
        # Convert tuples to sv.Point
        start_point = sv.Point(x=zone.start[0], y=zone.start[1])
        end_point = sv.Point(x=zone.end[0], y=zone.end[1])

        # Draw the line
        frame = sv.draw_line(
            scene=frame,
            start=start_point,
            end=end_point,
            color=self.zone_color,
            thickness=self.thickness,
        )

        # Draw stats if provided
        if stats is not None:
            # Position text at line midpoint
            mid_x = int((zone.start[0] + zone.end[0]) / 2)
            mid_y = int((zone.start[1] + zone.end[1]) / 2)
            text_anchor = sv.Point(x=mid_x, y=mid_y - 20)

            frame = sv.draw_text(
                scene=frame,
                text=str(stats),
                text_anchor=text_anchor,
                text_color=self.text_color,
                text_scale=self.text_scale,
                text_thickness=self.text_thickness,
                text_padding=self.text_padding,
                background_color=self.text_background_color,
            )

        return frame

    def draw_detections_in_zone(
        self,
        frame: np.ndarray,
        detections: sv.Detections,
        in_zone_mask: np.ndarray,
        labels: list[str] | None = None,
    ) -> np.ndarray:
        """
        Draw bounding boxes for detections in zone (highlighted).

        Args:
            frame: Video frame to draw on
            detections: All detections
            in_zone_mask: Boolean mask of which detections are in zone
            labels: Optional labels for each detection

        Returns:
            Frame with detections highlighted
        """
        if len(detections) == 0 or not in_zone_mask.any():
            return frame

        # Filter to in-zone detections
        zone_detections = detections[in_zone_mask]

        # Filter labels if provided
        zone_labels = None
        if labels is not None:
            zone_labels = [labels[i] for i, is_in_zone in enumerate(in_zone_mask) if is_in_zone]

        # Draw boxes using supervision BoxAnnotator
        box_annotator = sv.BoxAnnotator(
            color=self.zone_color,
            thickness=self.thickness,
        )

        # Draw labels if provided
        label_annotator = sv.LabelAnnotator(
            color=self.zone_color,
            text_color=self.text_color,
            text_scale=self.text_scale,
            text_thickness=self.text_thickness,
            text_padding=self.text_padding,
        ) if zone_labels else None

        frame = box_annotator.annotate(scene=frame.copy(), detections=zone_detections)

        if label_annotator and zone_labels:
            frame = label_annotator.annotate(
                scene=frame,
                detections=zone_detections,
                labels=zone_labels
            )

        return frame

    def draw_detection_trails(
        self,
        frame: np.ndarray,
        detections: sv.Detections,
        trace_length: int = 30,
    ) -> np.ndarray:
        """
        Draw trails for tracked detections (requires tracker_id).

        Args:
            frame: Video frame to draw on
            detections: Tracked detections
            trace_length: Length of trail history

        Returns:
            Frame with trails drawn
        """
        if detections.tracker_id is None or len(detections) == 0:
            return frame

        # Use supervision TraceAnnotator
        trace_annotator = sv.TraceAnnotator(
            color=self.zone_color,
            position=sv.Position.CENTER,
            trace_length=trace_length,
            thickness=self.thickness,
        )

        frame = trace_annotator.annotate(scene=frame.copy(), detections=detections)

        return frame

