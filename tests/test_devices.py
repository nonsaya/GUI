import os
from src.core.video_capture import list_v4l2_devices

def test_list_v4l2_devices():
    devs = list_v4l2_devices()
    assert isinstance(devs, list)
    for d in devs:
        assert d.startswith("/dev/video")
