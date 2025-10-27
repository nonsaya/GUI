import subprocess
from typing import List


def list_ros2_topics() -> List[str]:
    try:
        out = subprocess.check_output(["ros2", "topic", "list"], text=True, stderr=subprocess.STDOUT, timeout=2.0)
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        return lines
    except Exception:
        return []


def get_topic_type(topic: str) -> str:
    try:
        out = subprocess.check_output(["ros2", "topic", "type", topic], text=True, stderr=subprocess.STDOUT, timeout=2.0)
        return out.strip()
    except Exception:
        return "(unknown)"


def get_topic_sample(topic: str, timeout_sec: float = 1.5) -> str:
    try:
        # -n 1 で1メッセージのみ、短時間でタイムアウト
        out = subprocess.check_output(["ros2", "topic", "echo", "-n", "1", topic], text=True, stderr=subprocess.STDOUT, timeout=timeout_sec)
        return out.strip()
    except Exception as e:
        return "(no sample or timeout)"


