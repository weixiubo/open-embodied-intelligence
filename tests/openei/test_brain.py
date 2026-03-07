from __future__ import annotations

from openei.brain.speech_command import (
    SpeechCommandBrain,
    extract_duration_candidates,
    normalize_speech_text,
)
from openei.config import OpenEISettings
from openei.contracts import IntentKind, PerceptionEvent, RuntimeContext


def test_normalize_speech_text_supports_second_suffixes() -> None:
    assert normalize_speech_text("跳舞 10s") == "跳舞10秒"


def test_extract_duration_candidates_supports_chinese_numbers() -> None:
    assert extract_duration_candidates("跳舞十五秒") == [15]


def test_brain_creates_dance_plan_with_risk_flags() -> None:
    brain = SpeechCommandBrain(dance_action_labels=["挥手"])
    event = PerceptionEvent(
        source="test",
        modality="speech",
        raw_text="跳舞50秒",
        normalized_text="跳舞50秒",
    )

    plan = brain.plan(event, RuntimeContext(settings=OpenEISettings()))

    assert plan is not None
    assert plan.intent.kind == IntentKind.DANCE
    assert plan.intent.parameters["duration_seconds"] == 50
    assert "long_duration" in plan.intent.risk_flags
    assert plan.steps[0].action == "start_dance"


def test_brain_maps_named_action_to_dance_skill() -> None:
    brain = SpeechCommandBrain(dance_action_labels=["挥手"])
    event = PerceptionEvent(
        source="test",
        modality="speech",
        raw_text="执行动作挥手",
        normalized_text="执行动作挥手",
    )

    plan = brain.plan(event, RuntimeContext(settings=OpenEISettings()))

    assert plan is not None
    assert plan.intent.kind == IntentKind.ACTION
    assert plan.steps[0].parameters["action_label"] == "挥手"

