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


def get_topic_sample(topic: str, timeout_sec: float = 5.0) -> str:
    """
    Try to fetch one sample from a ROS 2 topic with several QoS variants.
    Returns a short textual sample or message on failure.
    """
    variants = [
        ["ros2", "topic", "echo", "-n", "1", topic],
        ["ros2", "topic", "echo", "-n", "1", "--qos-durability", "transient_local", topic],
        ["ros2", "topic", "echo", "-n", "1", "--qos-reliability", "best_effort", topic],
        ["ros2", "topic", "echo", "-n", "1", "--qos-durability", "transient_local", "--qos-reliability", "best_effort", topic],
    ]
    for cmd in variants:
        try:
            out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=timeout_sec)
            s = out.strip()
            if s:
                return s
        except Exception:
            continue
    return "(no sample or timeout)"


