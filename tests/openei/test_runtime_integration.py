from __future__ import annotations

from openei.config import InputMode, OpenEISettings, TransportMode
from openei.feedback import MemoryFeedbackSink
from openei.runtime import build_runtime_bundle


def test_runtime_runs_speech_to_confirmation_to_control_flow() -> None:
    settings = OpenEISettings(
        input_mode=InputMode.SCRIPTED,
        transport=TransportMode.SIM,
        confirm_dance_commands=False,
        confirm_high_risk_only=True,
    )
    bundle = build_runtime_bundle(settings=settings, scripted_inputs=["跳舞50秒", "确认"])
    sink = MemoryFeedbackSink()
    bundle.runtime.feedback = sink

    bundle.runtime.run(max_events=2)

    assert any("请确认" in message for message in sink.messages)
    assert any("确认执行" in message for message in sink.messages)
    assert bundle.runtime.control.inspect()["is_dancing"] is True


def test_runtime_runs_non_motion_skill_without_touching_control_loop() -> None:
    settings = OpenEISettings(
        input_mode=InputMode.SCRIPTED,
        transport=TransportMode.SIM,
    )
    bundle = build_runtime_bundle(settings=settings, scripted_inputs=["播报OpenEI准备好了"])
    sink = MemoryFeedbackSink()
    bundle.runtime.feedback = sink

    bundle.runtime.run(max_events=1)

    assert any("播报内容：openei准备好了" in message for message in sink.messages)
    assert bundle.runtime.control.inspect()["history_size"] == 0
