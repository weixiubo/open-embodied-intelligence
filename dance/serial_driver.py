"""
串口驱动模块。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from config import TransportMode, dance_config
from utils.logger import logger

try:
    import serial
    from serial.tools import list_ports

    SERIAL_AVAILABLE = True
except ImportError:
    serial = None
    list_ports = None
    SERIAL_AVAILABLE = False


@dataclass
class SerialHealth:
    requested_mode: str
    active_mode: str
    port: Optional[str]
    available_ports: List[str]
    connected: bool
    last_error: str = ""


class SerialDriver:
    """统一串口传输模式。"""

    def __init__(
        self,
        port: str = None,
        baudrate: int = None,
        transport: TransportMode = TransportMode.AUTO,
        auto_detect: bool = True,
    ) -> None:
        config = dance_config.servo
        self.port = port or config.serial_port
        self.baudrate = baudrate or config.baudrate
        self.transport = transport
        self.auto_detect = auto_detect and config.auto_detect
        self.is_connected = False
        self.last_error = ""
        self.available_ports: List[str] = []
        self._serial: Optional[object] = None  # 持久串口连接

        self._initialize_connection()

    def _initialize_connection(self) -> None:
        if self.transport == TransportMode.SIM:
            self.available_ports = self.scan_ports()
            logger.info("串口运行于模拟模式")
            return

        if not SERIAL_AVAILABLE:
            self.last_error = "pyserial 不可用"
            logger.warning("pyserial 未安装，将使用模拟模式")
            return

        self.available_ports = self.scan_ports()
        candidate_ports = []
        if self.port:
            candidate_ports.append(self.port)
        if self.auto_detect:
            candidate_ports.extend([item for item in self.available_ports if item not in candidate_ports])

        for candidate in candidate_ports:
            if self._open_port(candidate):
                self.port = candidate
                self.is_connected = True
                logger.info(f"串口连接成功: {self.port}")
                return

        self.last_error = "未找到可用串口"
        if self.transport == TransportMode.REAL:
            logger.error("真实硬件模式要求串口可用，但未找到设备")
        else:
            logger.warning("未找到可用串口，将使用模拟模式")

    def _test_port(self, port: str) -> bool:
        """仅检查设备节点是否存在（兼容旧逻辑）。"""
        if not port:
            return False
        if os.name != "nt" and not os.path.exists(port):
            return False
        return True

    def _open_port(self, port: str) -> bool:
        """尝试打开串口并保持持久连接。"""
        if not self._test_port(port):
            return False
        try:
            self._serial = serial.Serial(port, self.baudrate, timeout=1)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            logger.warning(f"串口 {port} 打开失败: {exc}")
            self._serial = None
            return False

    def close(self) -> None:
        """关闭串口连接。"""
        if self._serial and getattr(self._serial, 'is_open', False):
            self._serial.close()
        self._serial = None
        self.is_connected = False

    def send_action_command(self, seq: str) -> bool:
        if not self.is_connected:
            logger.info(f"模拟发送动作命令: Seq={seq}")
            return True

        # 如果持久连接已断开，尝试重连
        if self._serial is None or not getattr(self._serial, 'is_open', False):
            if not self._open_port(self.port):
                self.is_connected = False
                return False

        try:
            seq_int = int(seq)
            checksum = (seq_int + 0x44) & 0xFF
            command = bytes([0xA9, 0x9A, 0x03, 0x41, seq_int, checksum, 0xED]) + b"\n\r"
            self._serial.write(command)
            return True
        except Exception as exc:
            self.last_error = str(exc)
            logger.error(f"串口命令发送失败: {exc}")
            self.is_connected = False
            self.close()
            return False

    def get_status(self) -> dict:
        health = self.get_health()
        return {
            "connected": health.connected,
            "port": health.port,
            "baudrate": self.baudrate,
            "mode": health.active_mode,
            "requested_mode": health.requested_mode,
            "available_ports": health.available_ports,
            "last_error": health.last_error,
        }

    def get_health(self) -> SerialHealth:
        active_mode = "hardware" if self.is_connected else "simulation"
        if self.transport == TransportMode.REAL and not self.is_connected:
            active_mode = "unavailable"
        return SerialHealth(
            requested_mode=self.transport.value,
            active_mode=active_mode,
            port=self.port if self.is_connected else None,
            available_ports=self.available_ports,
            connected=self.is_connected,
            last_error=self.last_error,
        )

    @staticmethod
    def scan_ports() -> List[str]:
        ports: List[str] = []
        if SERIAL_AVAILABLE and list_ports is not None:
            ports.extend(port.device for port in list_ports.comports())
        for fallback in dance_config.servo.common_ports:
            if fallback not in ports and (os.name == "nt" or os.path.exists(fallback)):
                ports.append(fallback)
        return ports
