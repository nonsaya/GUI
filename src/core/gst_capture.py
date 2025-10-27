import threading
from queue import Queue, Empty
from typing import Optional, Tuple

import numpy as np

try:
    import gi  # type: ignore
    gi.require_version("Gst", "1.0")
    gi.require_version("GstApp", "1.0")
    from gi.repository import Gst, GstApp, GLib  # type: ignore
    Gst.init(None)
except Exception as e:  # pragma: no cover
    Gst = None  # type: ignore


class GStreamerCapture:
    """
    Minimal cv2.VideoCapture-like wrapper using GStreamer appsink.
    Supports camera (v4l2) and file input (decodebin).
    read() returns (ok, bgr_frame)
    """

    def __init__(self) -> None:
        self._pipeline: Optional[Gst.Pipeline] = None
        self._appsink: Optional[GstApp.AppSink] = None
        self._is_opened: bool = False
        self._queue: "Queue[np.ndarray]" = Queue(maxsize=2)
        self._width: int = 0
        self._height: int = 0
        self._fps: float = 0.0
        self._is_file: bool = False
        self._bus_watch_id: Optional[int] = None
        self._main_loop: Optional[GLib.MainLoop] = None
        self._loop_thread: Optional[threading.Thread] = None

    def open(self, source: str) -> bool:
        if Gst is None:
            return False
        self._is_file = not source.startswith("/dev/video")
        candidates = []
        if self._is_file:
            candidates = [
                (
                    f"filesrc location=\"{source}\" ! decodebin ! videorate drop-only=true max-rate=30 ! "
                    f"videoconvert n-threads=0 ! video/x-raw,format=BGR ! queue leaky=downstream max-size-buffers=1 ! "
                    f"appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true"
                )
            ]
        else:
            # 互換性最優先 → シンプル → NV12 1080p30 指定 → MJPEG フォールバック
            candidates = [
                (
                    f"v4l2src device=\"{source}\" ! videoconvert n-threads=0 ! "
                    f"video/x-raw,format=BGR ! queue leaky=downstream max-size-buffers=1 ! "
                    f"appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true"
                ),
                (
                    f"v4l2src device=\"{source}\" do-timestamp=true ! "
                    f"video/x-raw,format=NV12,width=1920,height=1080,framerate=30/1 ! "
                    f"videoconvert n-threads=0 ! video/x-raw,format=BGR,framerate=30/1 ! "
                    f"queue leaky=downstream max-size-buffers=1 ! appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true"
                ),
                (
                    f"v4l2src device=\"{source}\" do-timestamp=true ! image/jpeg,framerate=30/1 ! jpegdec ! "
                    f"videoconvert n-threads=0 ! video/x-raw,format=BGR,framerate=30/1 ! queue leaky=downstream max-size-buffers=1 ! "
                    f"appsink name=sink emit-signals=true sync=false max-buffers=1 drop=true"
                ),
            ]

        pipeline = None
        for launch in candidates:
            try:
                p = Gst.parse_launch(launch)
                if isinstance(p, Gst.Pipeline):
                    pipeline = p
                    break
            except Exception:
                continue
        if pipeline is None:
            return False

        self._pipeline = pipeline
        self._appsink = pipeline.get_by_name("sink")  # type: ignore
        if self._appsink is None:
            return False
        self._appsink.connect("new-sample", self._on_new_sample)
        # Bus watch (errors)
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)

        # Start GLib loop to deliver bus/messages in background
        self._main_loop = GLib.MainLoop()
        self._loop_thread = threading.Thread(target=self._main_loop.run, daemon=True)
        self._loop_thread.start()

        ret = pipeline.set_state(Gst.State.PLAYING)
        self._is_opened = ret == Gst.StateChangeReturn.ASYNC or ret == Gst.StateChangeReturn.SUCCESS
        return self._is_opened

    def _on_bus_message(self, bus, message):  # type: ignore
        t = message.type
        if t == Gst.MessageType.ERROR:
            self._is_opened = False
            try:
                err, debug = message.parse_error()
                # print or log if needed
            except Exception:
                pass

    def _on_new_sample(self, sink):  # type: ignore
        try:
            sample = sink.emit("pull-sample")
            buf = sample.get_buffer()
            caps = sample.get_caps()
            s = caps.get_structure(0)
            width = s.get_value("width")
            height = s.get_value("height")
            self._width = int(width)
            self._height = int(height)
            result, mapinfo = buf.map(Gst.MapFlags.READ)
            if not result:
                return Gst.FlowReturn.ERROR
            try:
                arr = np.frombuffer(mapinfo.data, dtype=np.uint8)
                arr = arr.reshape((self._height, self._width, 3))
                # push latest, drop old
                if self._queue.full():
                    try:
                        self._queue.get_nowait()
                    except Empty:
                        pass
                self._queue.put_nowait(arr.copy())
            finally:
                buf.unmap(mapinfo)
            return Gst.FlowReturn.OK
        except Exception:
            return Gst.FlowReturn.ERROR

    # cv2-like API
    def isOpened(self) -> bool:
        return self._is_opened

    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        try:
            frame = self._queue.get(timeout=0.5)
            return True, frame
        except Empty:
            return False, None

    def get(self, prop) -> float:
        # minimal mapping for FPS/size if queried
        if prop == 5:  # cv2.CAP_PROP_FPS
            return float(self._fps or 0.0)
        if prop == 3:  # cv2.CAP_PROP_FRAME_WIDTH
            return float(self._width or 0)
        if prop == 4:  # cv2.CAP_PROP_FRAME_HEIGHT
            return float(self._height or 0)
        if prop == 7:  # cv2.CAP_PROP_FRAME_COUNT (files)
            return 0.0
        return 0.0

    def release(self) -> None:
        if self._pipeline is not None:
            try:
                self._pipeline.set_state(Gst.State.NULL)
            except Exception:
                pass
        self._is_opened = False
        self._pipeline = None
        self._appsink = None
        if self._main_loop is not None:
            try:
                self._main_loop.quit()
            except Exception:
                pass
            self._main_loop = None
        # drain queue
        try:
            while True:
                self._queue.get_nowait()
        except Empty:
            pass


