import os
os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "xcb"))
from PyQt6 import QtWidgets, QtCore
from src.gui.app import VideoWidget
from src.core.video_capture import list_devices, DeviceDescriptor
from src.rviz.embed import RvizPane
from src.core.ros2_topics import list_ros2_topics

class NewMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("New GUI App with Capture")
        central = QtWidgets.QWidget()
        central.setStyleSheet("background-color: #2b2b2b; color: #e0e0e0;")
        self.setCentralWidget(central)

        self.video = VideoWidget()
        self.combo = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.open_btn = QtWidgets.QPushButton("Open File")
        self.rec_btn = QtWidgets.QPushButton("Rec")
        self.swap_btn = QtWidgets.QPushButton("Swap R/B")
        for b in [self.refresh_btn, self.start_btn, self.stop_btn, self.open_btn, self.rec_btn, self.swap_btn]:
            b.setStyleSheet("QPushButton{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:6px;} QPushButton:pressed{background-color:#505354;}")
        self.play_btn = QtWidgets.QPushButton("Play")
        self.pause_btn = QtWidgets.QPushButton("Pause")
        self.stop_play_btn = QtWidgets.QPushButton("Stop")
        for b in [self.play_btn, self.pause_btn, self.stop_play_btn]:
            b.setStyleSheet("QPushButton{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:6px;} QPushButton:pressed{background-color:#505354;}")
        self.speed_combo = QtWidgets.QComboBox()
        self.speed_combo.addItems(["0.5x","1x","2x"]) 
        self.speed_combo.setStyleSheet("QComboBox{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:4px;}")
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(0, 0)

        # Splitter: left (capture) | right (rviz)
        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.combo)
        hl.addWidget(self.refresh_btn)
        hl.addWidget(self.start_btn)
        hl.addWidget(self.stop_btn)
        hl.addWidget(self.open_btn)
        hl.addWidget(self.rec_btn)
        hl.addWidget(self.swap_btn)
        hl.addWidget(self.play_btn)
        hl.addWidget(self.pause_btn)
        hl.addWidget(self.stop_play_btn)
        hl.addWidget(self.speed_combo)

        self.rviz_pane = RvizPane()
        # ROS2 Topics Pane
        self.ros_panel = QtWidgets.QWidget()
        ros_layout = QtWidgets.QVBoxLayout(self.ros_panel)
        self.ros_refresh = QtWidgets.QPushButton("Refresh Topics")
        self.ros_refresh.setStyleSheet("QPushButton{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:6px;} QPushButton:pressed{background-color:#505354;}")
        self.ros_list = QtWidgets.QListWidget()
        self.ros_list.setStyleSheet("QListWidget{background-color:#2b2b2b;color:#e0e0e0;border:1px solid #555;}")
        ros_layout.addWidget(self.ros_refresh)
        ros_layout.addWidget(self.ros_list, 1)

        capture_panel = QtWidgets.QWidget()
        capture_panel.setStyleSheet("background-color: #2b2b2b;")
        cp_layout = QtWidgets.QVBoxLayout(capture_panel)
        cp_layout.addLayout(hl)
        cp_layout.addWidget(self.video, 1)
        cp_layout.addWidget(self.slider)

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(capture_panel)
        splitter.addWidget(self.rviz_pane)
        splitter.addWidget(self.ros_panel)
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
        self.swap_btn.clicked.connect(self.video.toggle_swap_rb)
        self.play_btn.clicked.connect(self._on_play)
        self.pause_btn.clicked.connect(self._on_pause)
        self.stop_play_btn.clicked.connect(self._on_stop_play)
        self.speed_combo.currentTextChanged.connect(self._on_speed)
        self.slider.sliderReleased.connect(self._on_seek)
        self.video.progress.connect(self._on_progress)
        self.ros_refresh.clicked.connect(self._on_ros_refresh)
        self._on_refresh()
        self._on_ros_refresh()

    def _on_refresh(self):
        self.combo.clear()
        devices = list_devices()
        for dev in devices:
            self.combo.addItem(dev.display_name, dev)
        preferred = -1
        for i in range(self.combo.count()):
            dev = self.combo.itemData(i)
            if isinstance(dev.open_arg, str) and dev.open_arg == "/dev/video0":
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
            # setup slider for file playback if frame count available
            try:
                total = int(self.video._total_frames)
                self.slider.setRange(0, total if total > 0 else 0)
            except Exception:
                self.slider.setRange(0, 0)
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

    def _on_play(self):
        if self.video._grabber is not None:
            self.video._grabber._paused = False

    def _on_pause(self):
        if self.video._grabber is not None:
            self.video._grabber._paused = True

    def _on_seek(self):
        if self.video._cap is None or not self.video._is_file:
            return
        pos = self.slider.value()
        try:
            self.video._cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        except Exception:
            pass
    def _on_progress(self, cur: int, total: int):
        try:
            if total and total > 0:
                self.slider.setRange(0, total)
            self.slider.blockSignals(True)
            self.slider.setValue(cur)
            self.slider.blockSignals(False)
        except Exception:
            pass

    def _on_stop_play(self):
        self.video.stop_playback()

    def _on_speed(self, text: str):
        speed = 1.0
        if text.endswith('x'):
            try:
                speed = float(text[:-1])
            except Exception:
                speed = 1.0
        self.video.set_play_speed(speed)

    def _on_ros_refresh(self):
        self.ros_list.clear()
        topics = list_ros2_topics()
        if not topics:
            self.ros_list.addItem("(no topics or ros2 not found)")
            return
        for t in topics:
            self.ros_list.addItem(t)


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = NewMainWindow()
    w.resize(1024, 640)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
