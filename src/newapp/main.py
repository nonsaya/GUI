import os
os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "xcb"))
from PyQt6 import QtWidgets, QtCore
from src.gui.app import VideoWidget
from src.core.video_capture import list_devices, DeviceDescriptor
from src.rviz.embed import RvizPane

class NewMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("New GUI App with Capture")
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        self.video = VideoWidget()
        self.combo = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.open_btn = QtWidgets.QPushButton("Open File")
        self.rec_btn = QtWidgets.QPushButton("Rec")

        # Splitter: left (capture) | right (rviz)
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.combo)
        hl.addWidget(self.refresh_btn)
        hl.addWidget(self.start_btn)
        hl.addWidget(self.stop_btn)
        hl.addWidget(self.open_btn)
        hl.addWidget(self.rec_btn)

        self.rviz_pane = RvizPane()

        capture_panel = QtWidgets.QWidget()
        cp_layout = QtWidgets.QVBoxLayout(capture_panel)
        cp_layout.addLayout(hl)
        cp_layout.addWidget(self.video, 1)

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(capture_panel)
        splitter.addWidget(self.rviz_pane)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QVBoxLayout(central)
        layout.addWidget(splitter)

        # Auto-start the first selected device
        QtCore.QTimer.singleShot(100, self._auto_start)

    def _auto_start(self):
        if self.combo.count() > 0:
            try:
                self._on_start()
            except Exception:
                pass

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
        preferred = -1
        for i in range(self.combo.count()):
            dev = self.combo.itemData(i)
            if isinstance(dev.open_arg, str) and dev.open_arg == "/dev/video2":
                try:
                    from src.core.video_capture import open_capture
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
                    from src.core.video_capture import open_capture
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
        self.video.pause_preview()
        try:
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Recording", "output.mp4", "MP4 Video (*.mp4)", options=options)
        finally:
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
    w = NewMainWindow()
    w.resize(1024, 640)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
