import supervision as sv


SOURCE_VIDEO_PATH = "./data/videos/vehicles-1280x720.mp4"

frames_generator sv.get_video_frames_generator(SOURCE_VIDEO_PATH)


START, END = sv.Point(x=0, y=1080), sv.Point(x=3840, y=1080)


tracker = sv.ByteTrack()
line_zone = sv.LineZone(start=START, end=END)




for frame in frames_generator:

    result = model(frame)[0]

    detections = sv.Detections.from_ultralytics(result)
    detections = tracker.update_with_detections(detections)

    crossed_in, crossed_out = line_zone.trigger(detections)
    print(crossed_in, crossed_out)



line_zone.in_count, linze_zone.out_count


