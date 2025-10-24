from PyQt6 import QtWidgets
from src.gui.app import VideoWidget
from src.core.video_capture import list_devices, DeviceDescriptor

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

        layout = QtWidgets.QVBoxLayout(central)
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
        for dev in list_devices():
            self.combo.addItem(dev.display_name, dev)

    def _on_start(self):
        if self.combo.count() == 0:
            QtWidgets.QMessageBox.warning(self, "No device", "V4L2 デバイスが見つかりません")
            return
        dev = self.combo.currentData()
        self.video.start(dev)

    def _on_open_file(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open Video", "", "Video Files (*.mp4 *.avi *.mkv);;All Files (*)")
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
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Recording", "output.mp4", "MP4 Video (*.mp4)")
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
