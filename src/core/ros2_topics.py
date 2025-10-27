import os
import shlex
import subprocess
from typing import List


def _build_ros2_shell(cmd: str) -> str:
    setup = os.environ.get("ROS2_SETUP", "")
    distro = os.environ.get("ROS_DISTRO", "")
    candidates = []
    if setup:
        candidates.append(setup)
    if distro:
        candidates.append(f"/opt/ros/{distro}/setup.bash")
    else:
        for d in ["humble", "iron", "jazzy", "foxy"]:
            candidates.append(f"/opt/ros/{d}/setup.bash")
    sources = "; ".join([f"[ -f {shlex.quote(p)} ] && source {shlex.quote(p)}" for p in candidates])
    if sources:
        return f"bash -lc '{sources}; {cmd}'"
    return f"bash -lc '{cmd}'"


def list_ros2_topics() -> List[str]:
    try:
        shell = _build_ros2_shell("ros2 topic list")
        out = subprocess.check_output(shell, shell=True, text=True, stderr=subprocess.STDOUT, timeout=3.0)
        lines = [line.strip() for line in out.splitlines() if line.strip()]
        return lines
    except Exception:
        return []


def get_topic_type(topic: str) -> str:
    try:
        shell = _build_ros2_shell(f"ros2 topic type {shlex.quote(topic)}")
        out = subprocess.check_output(shell, shell=True, text=True, stderr=subprocess.STDOUT, timeout=3.0)
        return out.strip()
    except Exception:
        return "(unknown)"


def get_topic_sample(topic: str, timeout_sec: float = 10.0) -> str:
    """
    Try to fetch one sample from a ROS 2 topic with several QoS variants.
    Returns a short textual sample or message on failure.
    """
    variants = [
        f"ros2 topic echo -n 1 {shlex.quote(topic)}",
        f"ros2 topic echo -n 1 --qos-durability transient_local {shlex.quote(topic)}",
        f"ros2 topic echo -n 1 --qos-reliability best_effort {shlex.quote(topic)}",
        f"ros2 topic echo -n 1 --qos-durability transient_local --qos-reliability best_effort {shlex.quote(topic)}",
    ]
    for cmd in variants:
        try:
            shell = _build_ros2_shell(cmd)
            out = subprocess.check_output(shell, shell=True, text=True, stderr=subprocess.STDOUT, timeout=timeout_sec)
            s = out.strip()
            if s:
                return s
        except Exception:
            continue
    return "(no sample or timeout)"


