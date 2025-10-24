from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import pyqtSignal, QThread
import cv2
import numpy as np
from src.core.video_capture import list_devices, DeviceDescriptor, open_capture
import time

class FrameGrabber(QThread):
    frame = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, cap: cv2.VideoCapture, parent=None):
        super().__init__(parent)
        self._cap = cap
        self._running = True

    def run(self):
        while self._running:
            try:
                ok, frame = self._cap.read()
                if not ok:
                    self.error.emit("Failed to read frame")
                    self.msleep(10)
                    continue
                self.frame.emit(frame)
            except Exception as e:
                self.error.emit(str(e))
                self.msleep(10)

    def stop(self):
        self._running = False
        self.wait(500)


class VideoWidget(QtWidgets.QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._cap = None
        self._grabber: FrameGrabber | None = None
        self._writer = None
        self._record_path = None
        self._record_fps = 30
        self._last_frame = None
        self._paused = False
        self._last_ts = None
        self._fps_ema = None
        self._swap_rb = False
    def _to_bgr(self, frame):
        bgr = None
        if frame.ndim == 2:
            try:
                bgr = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_NV12)
            except Exception:
                bgr = None
        elif frame.ndim == 3 and frame.shape[2] == 2:
            try:
                bgr = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_YUY2)
            except Exception:
                bgr = None
        if bgr is None:
            bgr = np.ascontiguousarray(frame)
        return bgr

    def start(self, device):
        if self._cap is not None:
            self.stop()
        self._cap = open_capture(device)
        self._grabber = FrameGrabber(self._cap, self)
        self._grabber.frame.connect(self._on_frame)
        self._grabber.error.connect(self._on_error)
        self._grabber.start()

    def stop(self):
        self.stop_recording()
        if self._grabber is not None:
            self._grabber.stop()
            self._grabber = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self.clear()
        self._paused = False

    def is_recording(self) -> bool:
        return self._writer is not None

    def start_recording(self, path: str):
        if self._cap is None:
            raise RuntimeError("Camera is not started")
        if self._writer is not None:
            return
        if self._last_frame is None:
            raise RuntimeError("No frame available yet; please wait a moment and try again")
        # Determine size and fps
        ema = self._fps_ema or 0
        devfps = (self._cap.get(cv2.CAP_PROP_FPS) or 0)
        fps = ema if ema > 0 else devfps
        if fps <= 1:
            fps = 30.0
        fps = float(max(5.0, min(60.0, fps)))
        w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # Prefer last captured frame to avoid racing with grabber
        if self._last_frame is not None:
            h, w = self._last_frame.shape[:2]
        if w <= 0 or h <= 0:
            raise RuntimeError("Invalid frame size for recording")
        # Choose codec/container with fallback candidates
        req = path
        candidates = []
        lower = req.lower()
        if lower.endswith('.avi'):
            candidates = [(req, 'MJPG'), (req, 'XVID')]
        elif lower.endswith('.mp4'):
            # prefer robust AVI first even if .mp4 requested
            candidates = [(req[:-4] + '.avi', 'MJPG'), (req[:-4] + '.avi', 'XVID'), (req, 'mp4v')]
        else:
            candidates = [(req + '.avi', 'MJPG'), (req + '.avi', 'XVID'), (req + '.mp4', 'mp4v')]

        opened = False
        out_path = None
        for out_path, codec in candidates:
            fourcc = cv2.VideoWriter_fourcc(*codec)
            writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
            if not writer.isOpened():
                continue
            # write a test frame to validate
            test_bgr = self._to_bgr(self._last_frame)
            if (test_bgr.shape[1], test_bgr.shape[0]) != (w, h):
                test_bgr = cv2.resize(test_bgr, (w, h), interpolation=cv2.INTER_AREA)
            try:
                writer.write(test_bgr)
                opened = True
                self._writer = writer
                break
            except Exception:
                writer.release()
                opened = False
                continue
        if not opened:
            raise RuntimeError("Failed to initialize any compatible VideoWriter (MJPG/XVID/mp4v)")
        self._record_path = out_path
        self._record_fps = int(fps)
        self._writer_size = (w, h)

    def stop_recording(self):
        if self._writer is not None:
            self._writer.release()
            self._writer = None
            self._record_path = None

    def _on_frame(self, frame):
        self._last_frame = frame
        # Update FPS estimate using exponential moving average
        now = time.monotonic()
        if self._last_ts is not None:
            dt = max(1e-6, now - self._last_ts)
            inst_fps = 1.0 / dt
            if self._fps_ema is None:
                self._fps_ema = inst_fps
            else:
                self._fps_ema = 0.9 * self._fps_ema + 0.1 * inst_fps
        self._last_ts = now
        # Convert NV12/YUY2 to BGR for writing/preview
        if self._paused:
            return
        # Convert NV12/YUY2 to BGR for writing/preview
        bgr = self._to_bgr(frame)
        h, w = bgr.shape[:2]
        bytes_per_line = 3 * w
        if getattr(self, "_swap_rb", False):
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            qimg = QtGui.QImage(rgb.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_RGB888)
        else:
            qimg = QtGui.QImage(bgr.data, w, h, bytes_per_line, QtGui.QImage.Format.Format_BGR888)
        pix = QtGui.QPixmap.fromImage(qimg).scaled(self.size(), QtCore.Qt.AspectRatioMode.KeepAspectRatio, QtCore.Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(pix)

    def toggle_swap_rb(self):
        self._swap_rb = not self._swap_rb
        # force repaint with swapped channels
        if self._last_frame is not None:
            self._on_frame(self._last_frame)

    def _on_error(self, msg: str):
        # keep silent to avoid spamming; could surface once
        pass

    def pause_preview(self):
        self._paused = True

    def resume_preview(self):
        self._paused = False

class MainWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("USB-C Capture GUI")
        self.video = VideoWidget()
        self.combo = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.open_btn = QtWidgets.QPushButton("Open File")
        self.rec_btn = QtWidgets.QPushButton("Rec")

        layout = QtWidgets.QVBoxLayout(self)
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.combo)
        hl.addWidget(self.refresh_btn)
        hl.addWidget(self.start_btn)
        hl.addWidget(self.stop_btn)
        hl.addWidget(self.open_btn)
        hl.addWidget(self.rec_btn)
        layout.addLayout(hl)
        layout.addWidget(self.video, 1)

        self.refresh_btn.clicked.connect(self._on_refresh)
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self.video.stop)
        self.open_btn.clicked.connect(self._on_open_file)
        self.rec_btn.clicked.connect(self._on_toggle_rec)

        self._on_refresh()

    def _on_refresh(self):
        self.combo.clear()
        devices = list_devices()
        for dev in devices:
            self.combo.addItem(dev.display_name, dev)
        # Prefer /dev/video2 if openable; otherwise first openable device
        preferred = -1
        for i in range(self.combo.count()):
            dev = self.combo.itemData(i)
            if isinstance(dev.open_arg, str) and dev.open_arg == "/dev/video2":
                try:
                    cap = open_capture(dev)
                    cap.release()
                    preferred = i
                    break
                except Exception:
                    pass
        if preferred < 0:
            for i in range(self.combo.count()):
                dev = self.combo.itemData(i)
                try:
                    cap = open_capture(dev)
                    cap.release()
                    preferred = i
                    break
                except Exception:
                    continue
        if preferred >= 0:
            self.combo.setCurrentIndex(preferred)

    def _on_start(self):
        if self.combo.count() == 0:
            QtWidgets.QMessageBox.warning(self, "No device", "V4L2 デバイスが見つかりません")
            return
        dev = self.combo.currentData()
        try:
            self.video.start(dev)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Start failed", str(e))

    def _on_open_file(self):
        options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video", "", "Video Files (*.mp4 *.avi *.mkv);;All Files (*)", options=options)
        if not path:
            return
        try:
            self.video.start(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Open failed", str(e))

    def _on_toggle_rec(self):
        if self.video.is_recording():
            self.video.stop_recording()
            self.rec_btn.setText("Rec")
            return
        if self.video._cap is None:
            QtWidgets.QMessageBox.warning(self, "Not started", "まずカメラまたはファイルを開始してください")
            return
        options = QtWidgets.QFileDialog.Option.DontUseNativeDialog
        # Temporarily pause preview to avoid dialog freeze on some environments
        self.video.pause_preview()
        try:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Recording", "output.mp4", "MP4 Video (*.mp4)", options=options)
        finally:
            # Resume preview if still not recording
            if (not self.video.is_recording()) and self.video._cap is not None:
                self.video.resume_preview()
        if not path:
            return
        try:
            self.video.start_recording(path)
            self.rec_btn.setText("Stop Rec")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Record failed", str(e))

def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.resize(960, 540)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
