import supervision as sv
import supervision.draw.utils as sv_draw
import numpy as np
from utils import get_target_run_folder

VIDEO_PATH = "./data/videos/vehicles-1280x720.mp4"


class ShapeAnimator:
    """
    Animates shapes based on frame progression.

    Design: Single Responsibility - encapsulates animation logic.
    Keeps draw_frame clean and testable.
    """

    def __init__(self, video_width: int, video_height: int):
        self.video_width = video_width
        self.video_height = video_height
        self.color_car_body = sv.Color(r=255, g=100, b=0)  # Orange
        self.color_wheels = sv.Color(r=50, g=50, b=50)     # Dark gray
        self.color_windows = sv.Color(r=100, g=200, b=255) # Light blue

    def get_car_position(self, frame_index: int) -> tuple[int, int]:
        """Calculate car position moving left-to-right with bounce."""
        progress = (frame_index * 15) % (self.video_width + 200)
        x = progress - 100
        y = self.video_height - 200
        return x, y

    def draw_simple_car(self, frame: np.ndarray, frame_index: int) -> np.ndarray:
        """Draw an animated car moving across the frame."""
        x, y = self.get_car_position(frame_index)

        # Car body (filled rectangle)
        car_body = sv.Rect(x=x, y=y, width=120, height=50)
        frame = sv_draw.draw_filled_rectangle(frame, rect=car_body, color=self.color_car_body)

        # Car roof (filled polygon - trapezoid)
        roof = np.array([
            [x + 20, y],
            [x + 90, y],
            [x + 75, y - 30],
            [x + 35, y - 30]
        ], dtype=np.int64)
        frame = sv_draw.draw_filled_polygon(frame, polygon=roof, color=self.color_car_body)

        # Windows (filled rectangles)
        front_window = sv.Rect(x=x + 55, y=y - 25, width=25, height=20)
        back_window = sv.Rect(x=x + 28, y=y - 25, width=25, height=20)
        frame = sv_draw.draw_filled_rectangle(frame, rect=front_window, color=self.color_windows)
        frame = sv_draw.draw_filled_rectangle(frame, rect=back_window, color=self.color_windows)

        # Wheels (filled circles via polygon approximation)
        wheel_y = y + 50
        wheel_radius = 15
        frame = self._draw_filled_circle(frame, center_x=x + 25, center_y=wheel_y, radius=wheel_radius, color=self.color_wheels)
        frame = self._draw_filled_circle(frame, center_x=x + 95, center_y=wheel_y, radius=wheel_radius, color=self.color_wheels)

        # Speed text
        speed_text = f"Frame {frame_index}"
        text_pos = sv.Point(x=x, y=y - 50)
        frame = sv_draw.draw_text(
            frame,
            text=speed_text,
            text_anchor=text_pos,
            text_color=sv.Color(r=255, g=255, b=255),
            text_scale=0.6,
            text_thickness=2
        )

        return frame

    def _draw_filled_circle(self, frame: np.ndarray, center_x: int, center_y: int, radius: int, color: sv.Color) -> np.ndarray:
        """Draw a filled circle using polygon approximation."""
        angles = np.linspace(0, 2 * np.pi, 30)
        points = np.array([
            [int(center_x + radius * np.cos(a)), int(center_y + radius * np.sin(a))]
            for a in angles
        ], dtype=np.int64)
        return sv_draw.draw_filled_polygon(frame, polygon=points, color=color)


def draw_frame(frame: np.ndarray, frame_index: int, animator: ShapeAnimator) -> np.ndarray:
    """
    Draw animated shapes on frame.

    Design: Delegates animation complexity to ShapeAnimator.
    Clean, single-purpose function.
    """
    return animator.draw_simple_car(frame, frame_index)


def process_video(video_path: str):
    TARGET_RUN_FOLDER = get_target_run_folder(application_name="draw")
    TARGET_VIDEO_PATH = f"{TARGET_RUN_FOLDER}/output.mp4"

    video_info = sv.VideoInfo.from_video_path(video_path)
    frames_generator = sv.get_video_frames_generator(video_path, stride=2)
    video_info.fps = 5

    # Initialize animator with video dimensions
    animator = ShapeAnimator(video_width=video_info.width, video_height=video_info.height)

    with sv.VideoSink(target_path=TARGET_VIDEO_PATH, video_info=video_info) as out_video_sink:
        frame_index = 0
        for frame in frames_generator:
            frame_index += 1
            if frame_index % 10 == 0:
                drawed_frame = draw_frame(frame.copy(), frame_index, animator)
                out_video_sink.write_frame(drawed_frame)
                sv.plot_image(drawed_frame, (12, 12))

    print(f"Video processing completed. Output: {TARGET_VIDEO_PATH}")




def main():
    process_video(VIDEO_PATH)
    pass


if __name__ == "__main__":
    main()