"""
舞蹈系统配置。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


@dataclass
class ServoConfig:
    # 香橙派 AI Pro 物理引脚 36 (UTXD2) / 11 (URXD2) 对应硬件 UART2 → /dev/ttyAMA1
    serial_port: str = "/dev/ttyAMA1"
    baudrate: int = 115200
    auto_detect: bool = True
    required: bool = False
    common_ports: tuple[str, ...] = (
        "/dev/ttyAMA1",  # 香橙派 AI Pro GPIO UART2（物理引脚 36/11）
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
    )

    def __post_init__(self) -> None:
        self.serial_port = _env("SERIAL_PORT", self.serial_port)
        self.baudrate = int(_env("SERIAL_BAUDRATE", str(self.baudrate)))
        self.auto_detect = _env("SERIAL_AUTO_DETECT", "true").lower() == "true"
        self.required = _env("SERIAL_REQUIRED", "false").lower() == "true"


@dataclass
class ChoreographyConfig:
    markov_enabled: bool = True
    music_weight: float = 0.7
    coherence_weight: float = 0.3
    temperature: float = 0.8
    history_length: int = 10
    beat_sync_enabled: bool = True
    beat_tolerance_ms: float = 50.0
    beat_prediction_enabled: bool = True
    diversity_penalty: float = 0.3
    max_repeat_count: int = 2


@dataclass
class DanceConfig:
    servo: ServoConfig = None
    choreography: ChoreographyConfig = None
    actions_file: str = "data/actions.csv"
    dance_stop_commands: tuple[str, ...] = ("停止跳舞", "不跳了", "停止舞蹈")
    dance_list_commands: tuple[str, ...] = ("舞蹈列表", "有什么舞蹈", "动作列表")

    def __post_init__(self) -> None:
        self.servo = ServoConfig()
        self.choreography = ChoreographyConfig()


dance_config = DanceConfig()
