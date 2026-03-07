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
    bundle = build_runtime_bundle(settings=settings, scripted_inputs=["\u8df3\u821e50\u79d2", "\u786e\u8ba4"])
    sink = MemoryFeedbackSink()
    bundle.runtime.feedback = sink

    bundle.runtime.run(max_events=2)

    assert any("Please confirm:" in message for message in sink.messages)
    assert any("Confirmed:" in message for message in sink.messages)
    assert bundle.runtime.control.inspect()["is_dancing"] is True
    assert bundle.runtime.inspect().state.history_size == 2


def test_runtime_runs_non_motion_skill_without_touching_control_loop() -> None:
    settings = OpenEISettings(
        input_mode=InputMode.SCRIPTED,
        transport=TransportMode.SIM,
    )
    bundle = build_runtime_bundle(settings=settings, scripted_inputs=["\u64ad\u62a5OpenEI\u51c6\u5907\u597d\u4e86"])
    sink = MemoryFeedbackSink()
    bundle.runtime.feedback = sink

    bundle.runtime.run(max_events=1)

    assert any("Announcement: openei\u51c6\u5907\u597d\u4e86" in message for message in sink.messages)
    assert bundle.runtime.control.inspect()["history_size"] == 0
