"""
Zone Visualizer Module
======================

Bounded Context: Zone and statistics visualization.

Design:
- SRP: Solo dibuja, no calcula
- Usa supervision.draw.utils (API coherente)
- Configurable: Color, estilos, posiciones

Dependencies:
- supervision (draw utils, Color, Point, Rect)
- numpy (arrays)
"""

import numpy as np
import supervision as sv
import supervision.draw.utils as sv_draw
from cupertino_zone.zone import PolygonZoneMonitor, LineZoneMonitor
from cupertino_zone.counter import ZoneStats


class ZoneVisualizer:
    """
    Visualizes zones and statistics on frames.

    Design: Compositor pattern - combina múltiples elementos visuales.
    """

    def __init__(
        self,
        zone_color: sv.Color = sv.Color(r=0, g=255, b=0),
        text_color: sv.Color = sv.Color(r=255, g=255, b=255),
        thickness: int = 2,
        text_scale: float = 0.6,
        opacity: float = 0.3,
    ):
        """
        Args:
            zone_color: Color for zone outline/fill
            text_color: Color for text labels
            thickness: Line thickness for drawing
            text_scale: Scale factor for text
            opacity: Opacity for zone fill (0-1)
        """
        self.zone_color = zone_color
        self.text_color = text_color
        self.thickness = thickness
        self.text_scale = text_scale
        self.opacity = opacity

    def draw_polygon_zone(
        self,
        frame: np.ndarray,
        zone: PolygonZoneMonitor,
        stats: ZoneStats | None = None,
    ) -> np.ndarray:
        """
        Draw a polygon zone on the frame.

        Args:
            frame: Video frame to draw on
            zone: PolygonZoneMonitor to visualize
            stats: Optional statistics to display

        Returns:
            Frame with zone drawn
        """
        # Draw filled polygon (with opacity)
        frame = sv_draw.draw_filled_polygon(
            frame,
            polygon=zone.polygon,
            color=self.zone_color,
            opacity=self.opacity,
        )

        # Draw polygon outline
        frame = sv_draw.draw_polygon(
            frame,
            polygon=zone.polygon,
            color=self.zone_color,
            thickness=self.thickness,
        )

        # Draw count text if stats provided
        if stats is not None:
            # Position text at top-left of polygon bounding box
            min_x = int(np.min(zone.polygon[:, 0]))
            min_y = int(np.min(zone.polygon[:, 1]))
            text_anchor = sv.Point(x=min_x, y=min_y - 10)

            frame = sv_draw.draw_text(
                frame,
                text=str(stats),
                text_anchor=text_anchor,
                text_color=self.text_color,
                text_scale=self.text_scale,
                text_thickness=self.thickness,
            )

        return frame

    def draw_line_zone(
        self,
        frame: np.ndarray,
        zone: LineZoneMonitor,
        display_counts: bool = True,
    ) -> np.ndarray:
        """
        Draw a line zone on the frame.

        Args:
            frame: Video frame to draw on
            zone: LineZoneMonitor to visualize
            display_counts: Whether to display in/out counts

        Returns:
            Frame with line drawn
        """
        # Draw the line
        frame = sv_draw.draw_line(
            frame,
            start=zone.start,
            end=zone.end,
            color=self.zone_color,
            thickness=self.thickness,
        )

        # Draw counts if enabled
        if display_counts:
            # Position text at line midpoint
            mid_x = int((zone.start.x + zone.end.x) / 2)
            mid_y = int((zone.start.y + zone.end.y) / 2)
            text_anchor = sv.Point(x=mid_x, y=mid_y - 20)

            count_text = f"IN: {zone.in_count} | OUT: {zone.out_count}"
            frame = sv_draw.draw_text(
                frame,
                text=count_text,
                text_anchor=text_anchor,
                text_color=self.text_color,
                text_scale=self.text_scale,
                text_thickness=self.thickness,
            )

        return frame

    def draw_detections_in_zone(
        self,
        frame: np.ndarray,
        detections: sv.Detections,
        in_zone_mask: np.ndarray,
    ) -> np.ndarray:
        """
        Draw bounding boxes for detections in zone (highlighted).

        Args:
            frame: Video frame to draw on
            detections: All detections
            in_zone_mask: Boolean mask of which detections are in zone

        Returns:
            Frame with detections highlighted
        """
        # Filter to in-zone detections
        zone_detections = detections[in_zone_mask]

        if len(zone_detections) == 0:
            return frame

        # Draw boxes using supervision BoxAnnotator
        box_annotator = sv.BoxAnnotator(
            color=self.zone_color,
            thickness=self.thickness,
        )
        frame = box_annotator.annotate(frame.copy(), detections=zone_detections)

        return frame
