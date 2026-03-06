"""
通用辅助函数。
"""

from __future__ import annotations

import os
import re
import time
from collections import deque
from pathlib import Path
from typing import Iterable, List, Optional


def find_serial_ports() -> List[str]:
    common_ports = [
        "/dev/ttyUSB0",
        "/dev/ttyUSB1",
        "/dev/ttyUSB2",
        "/dev/ttyAMA0",
        "/dev/ttyAMA1",
        "/dev/ttyS0",
        "/dev/ttyS1",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
    ]
    return [port for port in common_ports if os.path.exists(port)]


def test_serial_port(port: str, baudrate: int = 115200) -> bool:
    try:
        import serial

        with serial.Serial(port, baudrate, timeout=1):
            return True
    except Exception:
        return False


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}秒"
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    if remaining_seconds > 0:
        return f"{minutes}分{remaining_seconds:.0f}秒"
    return f"{minutes}分钟"


def ensure_directory(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


class Timer:
    """计时器上下文管理器。"""

    def __init__(self, name: str = "操作"):
        self.name = name
        self.start_time: Optional[float] = None
        self.elapsed: float = 0.0

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args) -> None:
        if self.start_time is not None:
            self.elapsed = time.perf_counter() - self.start_time

    def __str__(self) -> str:
        return f"{self.name}: {self.elapsed:.3f}秒"


_CN_BASIC = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def normalize_voice_text(text: str) -> str:
    """统一处理语音识别文本。"""
    if not text:
        return ""

    normalized = text.strip().lower()
    normalized = normalized.replace("秒钟", "秒")
    normalized = re.sub(r"(\d+)\s*(s|sec|seconds?)\b", r"\1秒", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    normalized = normalized.replace("确认一下", "确认")
    normalized = normalized.replace("开始跳舞", "跳舞")
    normalized = normalized.replace("开始舞蹈", "跳舞")
    return normalized


def _cn_to_int(text: str) -> Optional[int]:
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if len(text) == 1:
        return _CN_BASIC.get(text)
    if text[0] == "十":
        ones = _CN_BASIC.get(text[1], 0) if len(text) > 1 else 0
        return 10 + ones
    if len(text) >= 2 and text[1] == "十":
        tens = _CN_BASIC.get(text[0])
        if tens is None:
            return None
        ones = _CN_BASIC.get(text[2], 0) if len(text) > 2 else 0
        return tens * 10 + ones
    return None


def extract_duration_candidates(text: str) -> List[int]:
    """提取文本中的时长候选值。"""
    normalized = normalize_voice_text(text)
    results: List[int] = []

    for match in re.findall(r"(\d+)\s*秒", normalized):
        results.append(int(match))

    cn_pattern = (
        r"(十[一二三四五六七八九]?|"
        r"[一二三四五六七八九两]十[一二三四五六七八九]?|"
        r"[一二三四五六七八九两])秒"
    )
    for match in re.findall(cn_pattern, normalized):
        value = _cn_to_int(match)
        if value is not None:
            results.append(value)

    # 去重但保持顺序
    seen = set()
    deduped = []
    for value in results:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def extract_duration_from_text(text: str) -> Optional[int]:
    candidates = extract_duration_candidates(text)
    if not candidates:
        return None
    return candidates[0]


def rolling_average(values: Iterable[float], default: float = 0.0) -> float:
    collected = list(values)
    if not collected:
        return default
    return sum(collected) / len(collected)


class RollingWindow:
    """轻量滚动窗口。"""

    def __init__(self, maxlen: int):
        self._values = deque(maxlen=maxlen)

    def append(self, value: float) -> None:
        self._values.append(value)

    def clear(self) -> None:
        self._values.clear()

    def mean(self, default: float = 0.0) -> float:
        return rolling_average(self._values, default)

    def __len__(self) -> int:
        return len(self._values)

    def __iter__(self):
        return iter(self._values)
