import os
from datetime import datetime


def get_target_run_folder(application_name: str):
    # runs is datetime generated folder in the application name folder
    TARGET_RUN_FOLDER = f"./runs/{application_name}/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(TARGET_RUN_FOLDER, exist_ok=True)
    return TARGET_RUN_FOLDER