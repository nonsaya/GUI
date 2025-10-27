import subprocess
from typing import List


def list_ros2_topics() -> List[str]:
    try:
        out = subprocess.check_output(["ros2", "topic", "list"], text=True, stderr=subprocess.STDOUT, timeout=2.0)
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        return lines
    except Exception:
        return []


