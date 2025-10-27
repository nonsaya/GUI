import os
import pty
import selectors
import signal
import subprocess
import threading
from typing import Optional


class SSHTerminalSession:
    """
    Minimal SSH terminal session using system ssh with a pseudo-TTY.
    - Spawns: ssh -tt user@host -p port
    - Exposes write() for input and a background reader with callback for output.
    """

    def __init__(self, host: str, user: str, port: int = 22, identity_file: Optional[str] = None, password: Optional[str] = None, accept_new_hostkey: bool = True):
        self.host = host
        self.user = user
        self.port = port
        self.identity_file = identity_file
        self.password = password
        self.accept_new_hostkey = accept_new_hostkey
        self.proc: Optional[subprocess.Popen] = None
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self.on_output = None  # callback: (str) -> None
        self._password_sent = False

    def start(self) -> None:
        if self.proc is not None:
            return
        self.master_fd, self.slave_fd = pty.openpty()
        cmd = ["ssh"]
        if self.accept_new_hostkey:
            cmd += ["-o", "StrictHostKeyChecking=accept-new"]
        cmd += ["-tt", f"{self.user}@{self.host}", "-p", str(self.port)]
        if self.identity_file:
            cmd = ["ssh", "-i", self.identity_file, "-o", "StrictHostKeyChecking=accept-new", "-tt", f"{self.user}@{self.host}", "-p", str(self.port)]
        self.proc = subprocess.Popen(
            cmd,
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
            close_fds=True,
        )
        self._running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        if self.master_fd is None:
            return
        sel = selectors.DefaultSelector()
        sel.register(self.master_fd, selectors.EVENT_READ)
        try:
            while self._running and self.proc and self.proc.poll() is None:
                for key, _ in sel.select(timeout=0.2):
                    try:
                        data = os.read(key.fd, 4096)
                        if not data:
                            self._running = False
                            break
                        text = data.decode("utf-8", errors="replace")
                        # Handle prompts
                        low = text.lower()
                        if "(yes/no)" in low:
                            try:
                                self.write("yes\n")
                            except Exception:
                                pass
                        if ("password:" in low or "'s password:" in low or "password for" in low) and self.password and not self._password_sent:
                            try:
                                self.write(self.password + "\n")
                                self._password_sent = True
                            except Exception:
                                pass
                        if self.on_output:
                            try:
                                self.on_output(text)
                            except Exception:
                                pass
                    except OSError:
                        self._running = False
                        break
        finally:
            sel.close()

    def write(self, s: str) -> None:
        if self.master_fd is None:
            return
        try:
            os.write(self.master_fd, s.encode("utf-8", errors="replace"))
        except OSError:
            pass

    def set_password(self, password: Optional[str]) -> None:
        self.password = password
        self._password_sent = False

    def stop(self) -> None:
        self._running = False
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.send_signal(signal.SIGTERM)
        except Exception:
            pass
        try:
            if self.master_fd is not None:
                os.close(self.master_fd)
            if self.slave_fd is not None:
                os.close(self.slave_fd)
        except Exception:
            pass
        self.proc = None
        self.master_fd = None
        self.slave_fd = None

