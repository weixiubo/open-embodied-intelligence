"""
通用辅助函数

【版本说明】
- 原始文件：大创agentV3/utils/helpers.py  (未改动内容保留在下方)
- 本次新增：extract_duration_from_text()  支持从语音文本里提取"跳X秒"的时长
  调试开关：无需额外开关，纯纯解析函数，不影响运行时性能
"""

import os
import re
import time
from pathlib import Path
from typing import List, Optional


# ==================== 原始内容（未改动）====================

def find_serial_ports() -> List[str]:
    """
    查找可用的串口设备
    
    Returns:
        可用串口路径列表
    """
    common_ports = [
        "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyUSB2",
        "/dev/ttyAMA0", "/dev/ttyAMA1", "/dev/ttyAMA2",
        "/dev/ttyS0", "/dev/ttyS1", "/dev/ttyS2",
    ]
    
    available = []
    for port in common_ports:
        if os.path.exists(port):
            available.append(port)
    
    return available


def test_serial_port(port: str, baudrate: int = 115200) -> bool:
    """
    测试串口是否可用
    
    Args:
        port: 串口路径
        baudrate: 波特率
    
    Returns:
        是否可用
    """
    try:
        import serial
        with serial.Serial(port, baudrate, timeout=1) as ser:
            return True
    except ImportError:
        return False
    except Exception:
        return False


def format_duration(seconds: float) -> str:
    """
    格式化时长为可读字符串
    
    Args:
        seconds: 秒数
    
    Returns:
        格式化字符串，如 "1分30秒"
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if remaining_seconds > 0:
        return f"{minutes}分{remaining_seconds:.0f}秒"
    return f"{minutes}分钟"


def ensure_directory(path: Path) -> Path:
    """
    确保目录存在
    
    Args:
        path: 目录路径
    
    Returns:
        目录路径
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


class Timer:
    """计时器上下文管理器"""
    
    def __init__(self, name: str = "操作"):
        self.name = name
        self.start_time: Optional[float] = None
        self.elapsed: float = 0.0
    
    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args) -> None:
        if self.start_time:
            self.elapsed = time.perf_counter() - self.start_time
    
    def __str__(self) -> str:
        return f"{self.name}: {self.elapsed:.3f}秒"


# ==================== 新增：语音时长解析 ====================

# 中文数字基础映射（0-9）
_CN_BASIC = {
    '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
}


def _cn_to_int(s: str) -> Optional[int]:
    """
    将中文数字字符串（0-99范围）转为整数。
    支持: 五 / 十 / 十五 / 二十 / 三十五
    """
    if not s:
        return None
    # 纯阿拉伯数字（冗余保险）
    if s.isdigit():
        return int(s)
    # 单字中文数字
    if len(s) == 1:
        return _CN_BASIC.get(s, None)
    # "十" 开头 → 10~19
    if s[0] == '十':
        ones = _CN_BASIC.get(s[1], 0) if len(s) > 1 else 0
        return 10 + ones
    # "[二-九]十[零-九]?" → 20~99
    if len(s) >= 2 and s[1] == '十':
        tens = _CN_BASIC.get(s[0], 0)
        ones = _CN_BASIC.get(s[2], 0) if len(s) > 2 else 0
        result = tens * 10 + ones
        return result if result > 0 else None
    return None


def extract_duration_from_text(text: str) -> Optional[int]:
    """
    从语音识别文本中提取"跳 X 秒"的时长值（整数秒）。

    支持格式（X 可以是阿拉伯数字或中文数字）：
      - "跳5秒" / "跳 5 秒"
      - "跳五秒" / "跳二十秒" / "跳三十五秒"
      - 误识别形式 "要十秒" / "1二十秒"（使用者侧误识别容错，由调用方决定是否传入）

    返回：
        int  - 识别到的秒数
        None - 无法识别
    """
    if not text:
        return None

    # ---- 1. 优先匹配阿拉伯数字 ----
    m = re.search(r'(\d+)\s*秒', text)
    if m:
        return int(m.group(1))

    # ---- 2. 匹配中文数字 + 秒 ----
    # 覆盖范围：[一-九]? + 十 + [一-九]?  或  单个 [一-九两]
    cn_pattern = r'(十[一二三四五六七八九]?|[一二三四五六七八九两]十[一二三四五六七八九]?|[一二三四五六七八九两])秒'
    m = re.search(cn_pattern, text)
    if m:
        return _cn_to_int(m.group(1))

    return None
