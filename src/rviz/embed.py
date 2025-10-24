import os
import shlex
import subprocess
import time
from typing import Optional

from PyQt6 import QtCore, QtGui, QtWidgets


class RvizPane(QtWidgets.QWidget):
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None, display_config: Optional[str] = None):
        super().__init__(parent)
        self._rviz_proc: Optional[subprocess.Popen] = None
        self._container: Optional[QtWidgets.QWidget] = None
        self._display_config = display_config

        self.start_btn = QtWidgets.QPushButton("Start RViz2")
        self.stop_btn = QtWidgets.QPushButton("Stop RViz2")
        self.status_label = QtWidgets.QLabel("stopped")

        hl = QtWidgets.QHBoxLayout()
        hl.addWidget(self.start_btn)
        hl.addWidget(self.stop_btn)
        hl.addStretch(1)
        hl.addWidget(self.status_label)

        self._stack = QtWidgets.QStackedLayout()
        self._placeholder = QtWidgets.QLabel("RViz2 not running")
        self._placeholder.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._stack.addWidget(self._placeholder)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(hl)
        layout.addLayout(self._stack)

        self.start_btn.clicked.connect(self.start_rviz)
        self.stop_btn.clicked.connect(self.stop_rviz)

    def _find_rviz_window_id(self, pid: int, timeout_sec: float = 10.0) -> Optional[int]:
        end = time.time() + timeout_sec
        while time.time() < end:
            try:
                out = subprocess.check_output(["wmctrl", "-lp"], text=True)
            except Exception:
                return None
            for line in out.splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                win_id_hex = parts[0]
                try:
                    win_pid = int(parts[2])
                except ValueError:
                    continue
                if win_pid == pid:
                    try:
                        return int(win_id_hex, 16)
                    except ValueError:
                        continue
            time.sleep(0.2)
        return None

    def start_rviz(self):
        if self._rviz_proc and self._rviz_proc.poll() is None:
            return
        env = os.environ.copy()
        # Sanitize Qt plugin paths leaked from OpenCV/PyQt to avoid xcb plugin mismatch
        env.pop("QT_PLUGIN_PATH", None)
        env.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
        # Choose platform according to session type
        session_type = env.get("XDG_SESSION_TYPE", "").lower()
        if session_type == "wayland":
            # Wayland: run rviz2 externally (embedding unsupported), ensure wayland platform
            env["QT_QPA_PLATFORM"] = "wayland"
        else:
            # X11: prefer xcb for embeddability
            env["QT_QPA_PLATFORM"] = env.get("QT_QPA_PLATFORM", "xcb")
        args = ["rviz2"]
        if self._display_config:
            args += ["-d", self._display_config]
        try:
            self._rviz_proc = subprocess.Popen(args, env=env)
        except FileNotFoundError:
            QtWidgets.QMessageBox.critical(self, "rviz2 not found", "rviz2 コマンドが見つかりません。ROS 2 と rviz2 をインストールしてください。")
            return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Failed to start rviz2", str(e))
            return

        # Skip embedding on Wayland; show as external window
        if env.get("QT_QPA_PLATFORM") == "wayland":
            self.status_label.setText("running (external/wayland)")
            return

        win_id = self._find_rviz_window_id(self._rviz_proc.pid)
        if win_id is None:
            self.status_label.setText("running (external)")
            return
        qwin = QtGui.QWindow.fromWinId(win_id)
        self._container = QtWidgets.QWidget.createWindowContainer(qwin)
        self._stack.addWidget(self._container)
        self._stack.setCurrentWidget(self._container)
        self.status_label.setText("embedded")

    def stop_rviz(self):
        if self._container is not None:
            self._stack.setCurrentWidget(self._placeholder)
            self._stack.removeWidget(self._container)
            self._container.deleteLater()
            self._container = None
        if self._rviz_proc and self._rviz_proc.poll() is None:
            try:
                self._rviz_proc.terminate()
                self._rviz_proc.wait(timeout=3)
            except Exception:
                try:
                    self._rviz_proc.kill()
                except Exception:
                    pass
        self._rviz_proc = None
        self.status_label.setText("stopped")

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        self.stop_rviz()
        return super().closeEvent(event)


