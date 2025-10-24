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

        layout = QtWidgets.QVBoxLayout(central)
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.combo)
        hl.addWidget(self.refresh_btn)
        hl.addWidget(self.start_btn)
        hl.addWidget(self.stop_btn)
        layout.addLayout(hl)
        layout.addWidget(self.video, 1)

        self.refresh_btn.clicked.connect(self._on_refresh)
        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self.video.stop)
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


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = NewMainWindow()
    w.resize(1024, 640)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
