import os
os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "xcb"))
from PyQt6 import QtWidgets, QtCore
import re
from src.gui.app import VideoWidget
from src.core.video_capture import list_devices, DeviceDescriptor
from src.rviz.embed import RvizPane
from src.core.ros2_topics import list_ros2_topics, get_topic_type, get_topic_sample
from src.core.ssh_terminal import SSHTerminalSession
from src.core.ssh_paramiko import ParamikoTerminalSession

class NewMainWindow(QtWidgets.QMainWindow):
    ssh_out = QtCore.pyqtSignal(str)
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
        self.ros_info = QtWidgets.QTextEdit()
        self.ros_info.setReadOnly(True)
        self.ros_info.setStyleSheet("QTextEdit{background-color:#1f1f1f;color:#e0e0e0;border:1px solid #555;}")
        ros_layout.addWidget(self.ros_refresh)
        ros_layout.addWidget(self.ros_list, 1)
        ros_layout.addWidget(self.ros_info, 1)
        # SSH Terminal Pane
        self.ssh_panel = QtWidgets.QWidget()
        ssh_layout = QtWidgets.QVBoxLayout(self.ssh_panel)
        form = QtWidgets.QFormLayout()
        self.ssh_host = QtWidgets.QLineEdit("192.168.0.56")
        self.ssh_user = QtWidgets.QLineEdit("nonsaya-r")
        self.ssh_port = QtWidgets.QLineEdit("22")
        self.ssh_pass = QtWidgets.QLineEdit("")
        self.ssh_pass.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.ssh_pass.setPlaceholderText("Password (optional if key auth)")
        self.ssh_key = QtWidgets.QLineEdit("")
        self.ssh_key.setPlaceholderText("Identity file (e.g. ~/.ssh/id_ed25519)")
        self.ssh_key_browse = QtWidgets.QPushButton("Browse…")
        self.ssh_key_browse.setStyleSheet("QPushButton{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:6px;} QPushButton:pressed{background-color:#505354;}")
        for w in [self.ssh_host, self.ssh_user, self.ssh_port]:
            w.setStyleSheet("QLineEdit{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:4px;}")
        self.ssh_pass.setStyleSheet("QLineEdit{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:4px;}")
        self.ssh_key.setStyleSheet("QLineEdit{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:4px;}")
        form.addRow("HostName", self.ssh_host)
        form.addRow("User", self.ssh_user)
        form.addRow("Port", self.ssh_port)
        form.addRow("Password", self.ssh_pass)
        key_row = QtWidgets.QHBoxLayout()
        key_row.addWidget(self.ssh_key, 1)
        key_row.addWidget(self.ssh_key_browse)
        form.addRow("Identity file", key_row)
        self.ssh_connect = QtWidgets.QPushButton("Connect")
        self.ssh_connect.setStyleSheet("QPushButton{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:6px;} QPushButton:pressed{background-color:#505354;}")
        self.ssh_output = QtWidgets.QTextEdit()
        self.ssh_output.setReadOnly(True)
        self.ssh_output.setStyleSheet("QTextEdit{background-color:#1f1f1f;color:#e0e0e0;border:1px solid #555;}")
        self._ssh_prompt_color = "#00ff7f"  # default Green
        self.ssh_input = QtWidgets.QLineEdit()
        self.ssh_input.setPlaceholderText("Enter command and press Enter")
        self.ssh_input.setStyleSheet("QLineEdit{background-color:#3c3f41;color:#ffffff;border:1px solid #555;padding:4px;}")
        ssh_layout.addLayout(form)
        ssh_layout.addWidget(self.ssh_connect)
        ssh_layout.addWidget(self.ssh_output, 1)
        ssh_layout.addWidget(self.ssh_input)
        self._ssh_session = None

        capture_panel = QtWidgets.QWidget()
        capture_panel.setStyleSheet("background-color: #2b2b2b;")
        cp_layout = QtWidgets.QVBoxLayout(capture_panel)
        cp_layout.addLayout(hl)
        cp_layout.addWidget(self.video, 1)
        cp_layout.addWidget(self.slider)

        splitter = QtWidgets.QSplitter()
        splitter.setOrientation(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(capture_panel)
        # RViz2 は外部表示に切り替えたため、専用スペースは追加しない
        splitter.addWidget(self.ros_panel)
        splitter.addWidget(self.ssh_panel)
        splitter.setStretchFactor(0, 1)

        layout = QtWidgets.QVBoxLayout(central)
        # 上部バーにRViz2制御ボタンだけを追加
        rviz_bar = QtWidgets.QHBoxLayout()
        rviz_bar.addWidget(self.rviz_pane.start_btn)
        rviz_bar.addWidget(self.rviz_pane.stop_btn)
        rviz_bar.addWidget(self.rviz_pane.attach_btn)
        rviz_bar.addStretch(1)
        rviz_bar.addWidget(self.rviz_pane.status_label)

        layout.addLayout(rviz_bar)
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
        self.ros_list.itemSelectionChanged.connect(self._on_ros_select)
        self.ssh_connect.clicked.connect(self._on_ssh_connect)
        self.ssh_key_browse.clicked.connect(self._on_ssh_browse)
        self.ssh_input.returnPressed.connect(self._on_ssh_send)
        self.ssh_out.connect(self._append_ssh_output)
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
    def _on_ros_select(self):
        items = self.ros_list.selectedItems()
        if not items:
            self.ros_info.setPlainText("")
            return
        topic = items[0].text()
        self.ros_info.setPlainText("Fetching...")
        QtCore.QTimer.singleShot(50, lambda: self._load_topic_info(topic))

    def _load_topic_info(self, topic: str):
        t = get_topic_type(topic)
        s = get_topic_sample(topic)
        self.ros_info.setPlainText(f"Type: {t}\n\nSample:\n{s}")

    def _on_ssh_connect(self):
        host = self.ssh_host.text().strip()
        user = self.ssh_user.text().strip()
        try:
            port = int(self.ssh_port.text().strip() or "22")
        except Exception:
            port = 22
        if self._ssh_session is not None:
            try:
                self._ssh_session.stop()
            except Exception:
                pass
            self._ssh_session = None
        pwd = self.ssh_pass.text() or None
        key = self.ssh_key.text() or None
        ansi_osc = re.compile(r"\x1b\][^\x07]*\x07")
        ansi_csi = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
        ansi_si  = re.compile(r"\x1b\([A-Za-z]")
        def clean_ansi(t: str) -> str:
            t = t.replace("\r", "")
            t = ansi_osc.sub("", t)
            t = ansi_csi.sub("", t)
            t = ansi_si.sub("", t)
            return t
        def on_out(s: str):
            if s:
                self.ssh_out.emit(clean_ansi(s))
        # Prefer Paramiko; fallback to system ssh if it fails to start
        try:
            sess = ParamikoTerminalSession(host, user, port, identity_file=key, password=pwd, accept_new_hostkey=True)
            sess.on_output = on_out  # register BEFORE start to capture banner
            sess.start()
            self._ssh_session = sess
            using = "paramiko"
        except Exception as _:
            sess = SSHTerminalSession(host, user, port, identity_file=key, password=pwd, accept_new_hostkey=True)
            sess.on_output = on_out  # register BEFORE start
            try:
                sess.start()
                self._ssh_session = sess
                using = "system-ssh"
            except Exception as e2:
                self.ssh_output.append(f"Failed to connect: {e2}\n")
                return
        self.ssh_output.append(f"Connected to {user}@{host}:{port} via {using}\n")

    def _on_ssh_send(self):
        if self._ssh_session is None:
            return
        if not self._ssh_session.is_alive():
            self.ssh_output.append("(session ended)")
            return
        cmd = self.ssh_input.text() + "\n"
        self.ssh_input.clear()
        try:
            self._ssh_session.write(cmd)
        except Exception:
            pass
        # Allow Ctrl+C as ^C
        if cmd.strip().lower() in ["^c", "\u0003"]:
            try:
                self._ssh_session.write("\x03")
            except Exception:
                pass

    def _append_ssh_output(self, s: str):
        if not s:
            return
        # 1) 行に分割
        lines = s.splitlines()
        prompt_re = re.compile(r"^([A-Za-z0-9._-]+@[A-Za-z0-9._-]+:)(.*?)([$#])\s*$")
        def esc(t: str) -> str:
            return (t.replace("&", "&amp;")
                      .replace("<", "&lt;")
                      .replace(">", "&gt;"))
        for line in lines:
            m = prompt_re.match(line)
            if m:
                g1, g2, g3 = m.group(1), m.group(2), m.group(3)
                html = (
                    f'<span style="color:{self._ssh_prompt_color}; font-weight:600">{esc(g1)}</span>'
                    f'{esc(g2)}{esc(g3)}'
                )
                self.ssh_output.append(html)
            else:
                self.ssh_output.append(line)

    # 色選択UIは削除、固定色のまま運用

    def _on_ssh_browse(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select Identity File", os.path.expanduser("~/.ssh"), "All Files (*)")
        if path:
            self.ssh_key.setText(path)


def main():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    w = NewMainWindow()
    w.resize(1024, 640)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
