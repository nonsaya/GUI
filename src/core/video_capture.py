import os
from typing import List, Tuple

DEV_VIDEO_DIR = "/dev"

def list_v4l2_devices() -> List[str]:
    candidates = []
    try:
        for name in sorted(os.listdir(DEV_VIDEO_DIR)):
            if name.startswith("video"):
                candidates.append(os.path.join(DEV_VIDEO_DIR, name))
    except FileNotFoundError:
        return []
    return candidates

import cv2

def open_capture(device_path: str) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(device_path)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open capture: {device_path}")
    return cap
