"""
语音命令与确认流程测试。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import RecordingMode, RuntimeProfile, TransportMode, build_runtime_profile


def test_extract_duration_candidates_supports_digits_and_cn():
    from utils.helpers import extract_duration_candidates

    assert extract_duration_candidates("跳5秒") == [5]
    assert extract_duration_candidates("跳五秒") == [5]
    assert extract_duration_candidates("跳舞10s") == [10]


def test_parse_voice_intent_marks_inferred_duration_as_risky():
    from voice.intents import VoiceIntentType, parse_voice_intent

    intent = parse_voice_intent("要二十秒")
    assert intent.kind == VoiceIntentType.DANCE
    assert intent.duration_seconds == 20
    assert intent.is_high_risk is True


def test_robot_controller_requires_confirmation_in_demo_profile(monkeypatch):
    from dance.robot_controller import RobotController

    controller = RobotController(
        profile_config=build_runtime_profile(
            RuntimeProfile.DEMO,
            TransportMode.SIM,
            RecordingMode.SMART_VAD,
        )
    )
    called = {}

    def fake_start(duration: int) -> bool:
        called["duration"] = duration
        return True

    monkeypatch.setattr(controller, "start_dance", fake_start)

    assert controller.handle_voice_command("跳舞10秒") is True
    assert called == {}
    assert "确认" in controller.pop_feedback_message()

    assert controller.handle_voice_command("确认") is True
    assert called["duration"] == 10


def test_robot_controller_dev_profile_runs_safe_command_without_confirmation(monkeypatch):
    from dance.robot_controller import RobotController

    controller = RobotController(
        profile_config=build_runtime_profile(
            RuntimeProfile.DEV,
            TransportMode.SIM,
            RecordingMode.SMART_VAD,
        )
    )
    called = {}

    def fake_start(duration: int) -> bool:
        called["duration"] = duration
        return True

    monkeypatch.setattr(controller, "start_dance", fake_start)

    assert controller.handle_voice_command("跳五秒") is True
    assert called["duration"] == 5


def test_robot_controller_cancels_pending_command(monkeypatch):
    from dance.robot_controller import RobotController

    controller = RobotController(
        profile_config=build_runtime_profile(
            RuntimeProfile.DEMO,
            TransportMode.SIM,
            RecordingMode.SMART_VAD,
        )
    )
    monkeypatch.setattr(controller, "start_dance", lambda duration: True)

    assert controller.handle_voice_command("跳舞50秒") is True
    assert controller.handle_voice_command("取消") is True
    assert "取消" in controller.pop_feedback_message()
