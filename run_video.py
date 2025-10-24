import supervision as sv
from utils import get_target_run_folder

VIDEO_PATH = "./data/videos/vehicles-1280x720.mp4"



def process_video(video_path: str):
    TARGET_RUN_FOLDER = get_target_run_folder(application_name="video")

    video_info = sv.VideoInfo.from_video_path(video_path)
    # Adjust fps based on stride=2
    print(f"Video info: {video_info}")
    print(f"Video fps: {video_info.fps}")
    print(f"Video resolution: {video_info.resolution_wh}")
    video_info.fps = video_info.fps // 2

    frames_generator = sv.get_video_frames_generator(
        VIDEO_PATH,
        stride=2,
    )


    fps_monitor = sv.FPSMonitor()

    with sv.ImageSink(
        target_dir_path=TARGET_RUN_FOLDER,
        overwrite=True,
        image_name_pattern="frame_{:05d}.png"
        ) as out_image_sink:
        with sv.VideoSink(
            target_path=f"{TARGET_RUN_FOLDER}/output.mp4",
            video_info=video_info,
        ) as out_video_sink:

            frame_index = 0 # format 00000

            for frame in frames_generator:

                frame_index += 1

                if frame_index % 10 == 0:
                    out_image_sink.save_image(image=frame)
                    out_video_sink.write_frame(frame)
                    fps_monitor.tick()
                    print(f"FPS: {fps_monitor.fps}")

                if frame_index % 60 == 0:
                    sv.plot_image(frame, (12, 12))


    print(f"Video f{video_path} processing completed. Output video saved to {TARGET_RUN_FOLDER}/output.mp4")
    print(f"FPS: {fps_monitor.fps}")
    print(f"Total frames: {frame_index}")



def main():
    process_video(VIDEO_PATH)
    print("Done.")

if __name__ == "__main__":
    main()