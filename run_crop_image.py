import os
from pathlib import Path


"""

import matplotlib
show_plot = bool(os.environ.get("DISPLAY"))
if show_plot:
    matplotlib.use("TkAgg")
else:
    matplotlib.use("Agg")

if show_plot:
    try:
        sv.plot_image(image, (12, 12))
    except ImportError:
        print("Interactive backend unavailable; saving preview instead.")
        matplotlib.use("Agg", force=True)
        show_plot = False

if not show_plot:
    PREVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(PREVIEW_PATH)
    print(f"Saved preview to {PREVIEW_PATH}")

"""

import numpy as np
from PIL import Image
from datetime import datetime
import supervision as sv
from utils import get_target_run_folder

TARGET_RUN_FOLDER = get_target_run_folder(application_name="crop_image")

SOURCE_IMAGE_PATH = "./data/images/vehicles-1280x720__001.png"
SCALE_FACTOR = 0.5
RESOLUTION_WH = (320, 320)
CROPPED_XYXY = [200, 400, 600, 800]
OVERLAY_SHAPE = (100, 100, 3)
OVERLAY_ANCHOR = (50, 50)
PREVIEW_PATH = Path("samples/source_preview.png")


with sv.ImageSink(target_dir_path=TARGET_RUN_FOLDER) as sink:

    pil_image = Image.open(SOURCE_IMAGE_PATH).convert("RGB")
    image = np.array(pil_image)

    sink.save_image(image=image)


    print(f"Image size (width, height): {pil_image.size}")
    print(f"Image shape (H, W, C): {image.shape}")


    scaled_image = sv.scale_image(image=image.copy(), scale_factor=SCALE_FACTOR)
    print(f"Scaled shape: {scaled_image.shape}")
    sink.save_image(image=scaled_image)

    resized_image = sv.resize_image(image=image.copy(), resolution_wh=RESOLUTION_WH, keep_aspect_ratio=True)
    print(f"Resize shape: {resized_image.shape}")
    sink.save_image(image=resized_image)

    letterboxed_image = sv.letterbox_image(image=image.copy(), resolution_wh=RESOLUTION_WH)
    print(f"Letterboxed shape: {letterboxed_image.shape}")
    sink.save_image(image=letterboxed_image)


    overlay = np.zeros(OVERLAY_SHAPE, dtype=np.uint8)
    overlay_image = sv.overlay_image(image=image.copy(), overlay=overlay, anchor=OVERLAY_ANCHOR)
    print(f"Overlay image shape: {overlay_image.shape}")
    sink.save_image(image=overlay_image)

    cropped_image = sv.crop_image(image=image.copy(), xyxy=CROPPED_XYXY)
    print(f"Cropped shape: {cropped_image.shape}")
    sink.save_image(image=cropped_image)


sv.plot_images_grid(
    images=[image, cropped_image, overlay_image, scaled_image, resized_image, letterboxed_image],
    grid_size=(2, 3),
    titles=["Original", "Cropped", "Overlay", "Scaled", "Resized", "Letterboxed"],
)

print("Done.")
