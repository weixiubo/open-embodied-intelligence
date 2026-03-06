"""
舞蹈控制模块

包含机器人控制器、动作库、串口驱动等组件。
"""

from .robot_controller import RobotController
from .action_library import ActionLibrary
from .serial_driver import SerialDriver

__all__ = [
    'RobotController',
    'ActionLibrary',
    'SerialDriver',
]
