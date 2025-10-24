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
        # Try preferred backend first
        candidates = []
        if device.backend is not None:
            candidates.append((device.open_arg, device.backend))
        candidates.append((device.open_arg, None))  # fallback to CAP_ANY
        last_err = None
        for open_arg, backend in candidates:
            try:
                cap = cv2.VideoCapture(open_arg, backend) if backend is not None else cv2.VideoCapture(open_arg)
                # Prefer MJPG for performance if supported
                try:
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                except Exception:
                    pass
                # Reduce internal buffering to minimize stutter/latency
                try:
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except Exception:
                    pass
                # Try to limit FPS to 30 to avoid drop/fast-forward perception
                try:
                    cap.set(cv2.CAP_PROP_FPS, 30)
                except Exception:
                    pass
                # Ensure backend returns BGR frames
                try:
                    cap.set(cv2.CAP_PROP_CONVERT_RGB, 1)
                except Exception:
                    pass
                if not cap.isOpened():
                    cap.release()
                    raise RuntimeError("isOpened() failed")
                ok, _ = cap.read()
                if not ok:
                    cap.release()
                    raise RuntimeError("read() failed")
                return cap
            except Exception as e:
                last_err = e
                continue
        raise RuntimeError(f"Failed to open capture: {device.display_name}: {last_err}")
    # Backward compatibility with string path/index
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open capture: {device}")
    ok, _ = cap.read()
    if not ok:
        cap.release()
        raise RuntimeError(f"Failed to read from: {device}")
    return cap
