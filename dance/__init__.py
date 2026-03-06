"""
舞蹈控制模块

提供动作库管理、机器人控制、串口驱动等功能。
"""

from .action_library import ActionLibrary, DanceAction
from .robot_controller import RobotController
from .serial_driver import SerialDriver

__all__ = [
    "ActionLibrary",
    "DanceAction",
    "RobotController",
    "SerialDriver",
]
