"""
运行时配置。

定义演示模式、传输模式和录音模式，供入口、自检和语音链路共享。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeProfile(str, Enum):
    DEV = "dev"
    DEMO = "demo"


class TransportMode(str, Enum):
    AUTO = "auto"
    REAL = "real"
    SIM = "sim"


class RecordingMode(str, Enum):
    SMART_VAD = "smart_vad"
    PUSH_TO_TALK = "push_to_talk"
    FIXED_DURATION = "fixed_duration"


@dataclass(frozen=True)
class DemoProfileConfig:
    """运行时配置快照。"""

    profile: RuntimeProfile
    transport: TransportMode
    recording_mode: RecordingMode
    enable_startup_checks: bool
    confirm_dance_commands: bool
    confirm_high_risk_only: bool
    allow_cloud_fallback: bool
    startup_greeting: str
    show_status_panel: bool = True


def build_runtime_profile(
    profile: RuntimeProfile,
    transport: TransportMode,
    recording_mode: RecordingMode,
) -> DemoProfileConfig:
    """构建运行时配置。"""
    if profile == RuntimeProfile.DEMO:
        return DemoProfileConfig(
            profile=profile,
            transport=transport,
            recording_mode=recording_mode,
            enable_startup_checks=True,
            confirm_dance_commands=True,
            confirm_high_risk_only=False,
            allow_cloud_fallback=True,
            startup_greeting="智能舞蹈机器人已就绪。",
            show_status_panel=True,
        )

    return DemoProfileConfig(
        profile=profile,
        transport=transport,
        recording_mode=recording_mode,
        enable_startup_checks=True,
        confirm_dance_commands=False,
        confirm_high_risk_only=True,
        allow_cloud_fallback=True,
        startup_greeting="语音助手已启动。",
        show_status_panel=True,
    )
