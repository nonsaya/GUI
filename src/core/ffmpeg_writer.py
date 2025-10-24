import shutil
import subprocess
from typing import Optional


class FFMpegWriter:
    def __init__(self):
        self.proc: Optional[subprocess.Popen] = None
        self.width = 0
        self.height = 0

    def is_available(self) -> bool:
        return shutil.which("ffmpeg") is not None

    def open(self, path: str, width: int, height: int, fps: float) -> None:
        if not self.is_available():
            raise RuntimeError("ffmpeg not found")
        self.width = width
        self.height = height
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "rawvideo",
            "-pix_fmt", "bgr24",
            "-video_size", f"{width}x{height}",
            "-framerate", f"{fps:.2f}",
            "-i", "-",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            path if path.lower().endswith(".mp4") else path + ".mp4",
        ]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        if self.proc.stdin is None:
            raise RuntimeError("Failed to open ffmpeg stdin")

    def write(self, bgr_frame) -> None:
        if not self.proc or not self.proc.stdin:
            return
        self.proc.stdin.write(bgr_frame.tobytes())

    def close(self) -> None:
        if self.proc and self.proc.stdin:
            try:
                self.proc.stdin.flush()
                self.proc.stdin.close()
            except Exception:
                pass
        if self.proc:
            try:
                self.proc.wait(timeout=5)
            except Exception:
                self.proc.kill()
        self.proc = None


