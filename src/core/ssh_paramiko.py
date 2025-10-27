import os
import threading
from typing import Optional, Callable

import paramiko


class ParamikoTerminalSession:
    def __init__(self, host: str, user: str, port: int = 22, identity_file: Optional[str] = None, password: Optional[str] = None, accept_new_hostkey: bool = True):
        self.host = host
        self.user = user
        self.port = port
        self.identity_file = os.path.expanduser(identity_file) if identity_file else None
        self.password = password
        self.accept_new_hostkey = accept_new_hostkey
        self.client: Optional[paramiko.SSHClient] = None
        self.chan: Optional[paramiko.Channel] = None
        self._reader_thread: Optional[threading.Thread] = None
        self._running = False
        self.on_output: Optional[Callable[[str], None]] = None

    def start(self) -> None:
        if self.client is not None:
            return
        self.client = paramiko.SSHClient()
        if self.accept_new_hostkey:
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        else:
            self.client.load_system_host_keys()

        pkey = None
        if self.identity_file and os.path.exists(self.identity_file):
            try:
                try:
                    pkey = paramiko.Ed25519Key.from_private_key_file(self.identity_file, password=self.password)
                except Exception:
                    pkey = paramiko.RSAKey.from_private_key_file(self.identity_file, password=self.password)
            except Exception:
                pkey = None

        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password if not pkey else None,
            pkey=pkey,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
        self.chan = self.client.get_transport().open_session()
        self.chan.get_pty(term='xterm', width=120, height=32)
        self.chan.invoke_shell()
        self._running = True
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._reader_thread.start()

    def _reader_loop(self) -> None:
        if not self.chan:
            return
        try:
            while self._running and not self.chan.exit_status_ready():
                if self.chan.recv_ready():
                    data = self.chan.recv(4096)
                    if not data:
                        break
                    text = data.decode('utf-8', errors='replace')
                    if self.on_output:
                        try:
                            self.on_output(text)
                        except Exception:
                            pass
                else:
                    self.chan.recv_ready()
        finally:
            pass

    def write(self, s: str) -> None:
        if self.chan and self.chan.send_ready():
            try:
                self.chan.send(s)
            except Exception:
                pass

    def is_alive(self) -> bool:
        return bool(self.chan and not self.chan.closed)

    def stop(self) -> None:
        self._running = False
        try:
            if self.chan:
                self.chan.close()
        except Exception:
            pass
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass
        self.chan = None
        self.client = None


