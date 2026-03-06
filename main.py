#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能语音舞蹈机器人入口。
"""

from __future__ import annotations

import argparse
import signal
import sys

from config import (
    RecordingMode,
    RuntimeProfile,
    TransportMode,
    build_runtime_profile,
    settings,
)
from dance import RobotController
from utils.logger import logger
from utils.startup_checks import run_startup_checks
from voice import VoiceAssistant


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="智能舞蹈机器人")
    parser.add_argument(
        "--profile",
        choices=[item.value for item in RuntimeProfile],
        default=RuntimeProfile.DEMO.value,
        help="运行配置档位",
    )
    parser.add_argument(
        "--transport",
        choices=[item.value for item in TransportMode],
        default=TransportMode.AUTO.value,
        help="硬件传输模式",
    )
    parser.add_argument(
        "--recording-mode",
        choices=[item.value for item in RecordingMode],
        default=RecordingMode.SMART_VAD.value,
        help="录音模式",
    )
    parser.add_argument(
        "--no-tts",
        action="store_true",
        help="禁用 TTS 播报",
    )
    return parser.parse_args()


def _print_status_panel(robot: RobotController, profile_name: str, transport_name: str, recording_name: str) -> None:
    status = robot.get_status()
    print("=== 演示状态 ===")
    print(f"Profile : {profile_name}")
    print(f"Transport: {transport_name}")
    print(f"Recording: {recording_name}")
    print(f"Serial   : {status['serial']['mode']}")
    print(f"Actions  : {status['action_count']}")
    print("================")


def main() -> int:
    args = parse_args()
    runtime_config = build_runtime_profile(
        RuntimeProfile(args.profile),
        TransportMode(args.transport),
        RecordingMode(args.recording_mode),
    )

    report = run_startup_checks(runtime_config)
    if report.has_blocking_failures:
        logger.error("启动自检未通过，已阻断启动")
        print(report.render())
        return 2

    robot = RobotController(profile_config=runtime_config)
    assistant = VoiceAssistant(
        runtime_config=runtime_config,
        use_tts=not args.no_tts,
    )
    assistant.set_dance_handler(robot)
    robot.set_voice_assistant(assistant)

    def _shutdown(signum, frame) -> None:
        _ = signum, frame
        logger.info("收到退出信号，正在停止系统")
        assistant.stop()
        if robot.is_dancing:
            robot.stop_dance()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    if not settings.silent_startup and runtime_config.show_status_panel:
        _print_status_panel(robot, args.profile, args.transport, args.recording_mode)

    try:
        assistant.run_voice_chat()
        return 0
    except KeyboardInterrupt:
        logger.info("收到中断信号")
        return 0
    except Exception as exc:
        logger.error(f"系统错误: {exc}", exc_info=True)
        print(f"系统错误: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
