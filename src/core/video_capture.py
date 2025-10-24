import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Union

import cv2

DEV_VIDEO_DIR = "/dev"


@dataclass
class DeviceDescriptor:
    id: str
    display_name: str
    open_arg: Union[str, int]
    backend: Optional[int] = None


def list_v4l2_devices() -> List[str]:
    candidates: List[str] = []
    try:
        for name in sorted(os.listdir(DEV_VIDEO_DIR)):
            if name.startswith("video"):
                candidates.append(os.path.join(DEV_VIDEO_DIR, name))
    except FileNotFoundError:
        return []
    return candidates


def list_devices() -> List[DeviceDescriptor]:
    devices: List[DeviceDescriptor] = []
    if sys.platform.startswith("linux"):
        for path in list_v4l2_devices():
            devices.append(
                DeviceDescriptor(
                    id=path,
                    display_name=path,
                    open_arg=path,
                    backend=cv2.CAP_V4L2,
                )
            )
    elif sys.platform.startswith("win"):
        # Probe first several indices via DirectShow; if unavailable, fallback to MSMF
        preferred_backends = [cv2.CAP_DSHOW, cv2.CAP_MSMF]
        max_index = 10
        for index in range(0, max_index):
            opened = False
            chosen_backend: Optional[int] = None
            for backend in preferred_backends:
                cap = cv2.VideoCapture(index, backend)
                if cap.isOpened():
                    cap.release()
                    opened = True
                    chosen_backend = backend
                    break
            if opened:
                backend_name = "DirectShow" if chosen_backend == cv2.CAP_DSHOW else "MediaFoundation"
                devices.append(
                    DeviceDescriptor(
                        id=f"index:{index}",
                        display_name=f"Camera {index} ({backend_name})",
                        open_arg=index,
                        backend=chosen_backend,
                    )
                )
    else:
        # Other platforms: best-effort probe numeric indices
        for index in range(0, 5):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                cap.release()
                devices.append(
                    DeviceDescriptor(
                        id=f"index:{index}",
                        display_name=f"Camera {index}",
                        open_arg=index,
                        backend=None,
                    )
                )
    return devices


def open_capture(device: Union[str, DeviceDescriptor]) -> cv2.VideoCapture:
    if isinstance(device, DeviceDescriptor):
        if device.backend is not None:
            cap = cv2.VideoCapture(device.open_arg, device.backend)
        else:
            cap = cv2.VideoCapture(device.open_arg)
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open capture: {device.display_name}")
        # Probe one frame to validate stream (avoid silent failures like 'moov atom not found')
        ok, _ = cap.read()
        if not ok:
            cap.release()
            raise RuntimeError(f"Failed to read from: {device.display_name}")
        return cap
    # Backward compatibility with string path/index
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open capture: {device}")
    ok, _ = cap.read()
    if not ok:
        cap.release()
        raise RuntimeError(f"Failed to read from: {device}")
    return cap
