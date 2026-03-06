"""
启动自检。
"""

from __future__ import annotations

import importlib.util
import platform
import shutil
import socket
from dataclasses import dataclass, field
from typing import List

from config import DemoProfileConfig, RuntimeProfile, TransportMode, api_config, settings
from utils.logger import logger


@dataclass
class StartupCheckItem:
    name: str
    status: str
    message: str
    critical: bool = False


@dataclass
class StartupCheckReport:
    items: List[StartupCheckItem] = field(default_factory=list)

    def add(self, name: str, status: str, message: str, critical: bool = False) -> None:
        self.items.append(StartupCheckItem(name=name, status=status, message=message, critical=critical))

    @property
    def has_blocking_failures(self) -> bool:
        return any(item.status == "fail" and item.critical for item in self.items)

    def render(self) -> str:
        lines = ["启动自检结果:"]
        for item in self.items:
            lines.append(f"- [{item.status.upper()}] {item.name}: {item.message}")
        return "\n".join(lines)


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _check_network(host: str, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, 443), timeout=timeout):
            return True
    except OSError:
        return False


def run_startup_checks(profile: DemoProfileConfig) -> StartupCheckReport:
    report = StartupCheckReport()

    report.add(
        "环境文件",
        "pass" if settings.env_file.exists() else "warn",
        "检测到 .env 文件" if settings.env_file.exists() else "未检测到 .env 文件，将按降级模式运行",
    )

    if api_config.baidu.is_configured:
        report.add("百度语音", "pass", "百度语音配置完整")
    else:
        report.add("百度语音", "warn", "百度语音配置不完整，语音功能将降级", critical=False)

    if api_config.deepseek.is_configured:
        report.add("DeepSeek", "pass", "DeepSeek 配置完整")
    else:
        report.add("DeepSeek", "warn", "DeepSeek 未配置，将使用脚本化回复", critical=False)

    report.add(
        "PyAudio",
        "pass" if _module_available("pyaudio") else "fail",
        "可进行实时录音" if _module_available("pyaudio") else "缺少 pyaudio",
        critical=profile.transport == TransportMode.REAL,
    )
    report.add(
        "librosa",
        "pass" if _module_available("librosa") else "warn",
        "可进行实时音乐分析" if _module_available("librosa") else "缺少 librosa，将切换基础节拍模式",
    )
    report.add(
        "pyserial",
        "pass" if _module_available("serial") else "warn",
        "可进行串口控制" if _module_available("serial") else "缺少 pyserial，将切到模拟模式",
    )

    network_ok = _check_network("api.deepseek.com") or _check_network("vop.baidu.com")
    report.add(
        "网络",
        "pass" if network_ok else "warn",
        "外网可达" if network_ok else "外网不可达，云端能力可能降级",
    )

    if platform.system() == "Linux":
        speaker_ready = any(shutil.which(player) for player in ("mpg123", "mpv", "ffplay", "aplay"))
    else:
        speaker_ready = True
    report.add(
        "音频播放",
        "pass" if speaker_ready else "warn",
        "可播放提示音/TTS" if speaker_ready else "未找到播放器，TTS 将只输出日志",
    )

    # 传输模式只做静态提示，真实串口检查交给 SerialDriver。
    if profile.transport == TransportMode.SIM:
        report.add("传输模式", "pass", "强制模拟模式")
    elif profile.transport == TransportMode.AUTO:
        report.add("传输模式", "pass", "自动在真实/模拟模式之间切换")
    else:
        report.add("传输模式", "pass", "强制真实硬件模式", critical=True)

    logger.info(report.render())
    return report
