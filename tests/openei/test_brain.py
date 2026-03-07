from __future__ import annotations

from openei.brain import DeterministicSpeechBrain, LLMAssistedSpeechBrain
from openei.brain.speech_command import extract_duration_candidates, normalize_speech_text
from openei.config import OpenEISettings
from openei.contracts import IntentKind, PerceptionEvent, RuntimeContext


def test_normalize_speech_text_supports_second_suffixes() -> None:
    assert normalize_speech_text("\u8df3\u821e 10s") == "\u8df3\u821e10\u79d2"


def test_extract_duration_candidates_supports_chinese_numbers() -> None:
    assert extract_duration_candidates("\u8df3\u821e\u5341\u4e94\u79d2") == [15]


def test_brain_creates_dance_plan_with_risk_flags() -> None:
    brain = DeterministicSpeechBrain(dance_action_labels=["\u6325\u624b"])
    event = PerceptionEvent(
        source="test",
        modality="speech",
        raw_text="\u8df3\u821e50\u79d2",
        normalized_text="\u8df3\u821e50\u79d2",
    )

    plan = brain.plan(event, RuntimeContext(settings=OpenEISettings()))

    assert plan is not None
    assert plan.intent.kind == IntentKind.DANCE
    assert plan.intent.parameters["duration_seconds"] == 50
    assert "long_duration" in plan.intent.risk_flags
    assert plan.steps[0].action == "start_dance"
    assert plan.metadata["brain_mode"] == "deterministic"


def test_brain_maps_named_action_to_dance_skill() -> None:
    brain = DeterministicSpeechBrain(dance_action_labels=["\u6325\u624b"])
    event = PerceptionEvent(
        source="test",
        modality="speech",
        raw_text="\u6267\u884c\u52a8\u4f5c\u6325\u624b",
        normalized_text="\u6267\u884c\u52a8\u4f5c\u6325\u624b",
    )

    plan = brain.plan(event, RuntimeContext(settings=OpenEISettings()))

    assert plan is not None
    assert plan.intent.kind == IntentKind.ACTION
    assert plan.steps[0].parameters["action_label"] == "\u6325\u624b"


def test_brain_maps_announcement_to_non_motion_skill() -> None:
    brain = DeterministicSpeechBrain(dance_action_labels=["\u6325\u624b"])
    event = PerceptionEvent(
        source="test",
        modality="speech",
        raw_text="\u64ad\u62a5OpenEI\u51c6\u5907\u597d\u4e86",
        normalized_text="\u64ad\u62a5openei\u51c6\u5907\u597d\u4e86",
    )

    plan = brain.plan(event, RuntimeContext(settings=OpenEISettings()))

    assert plan is not None
    assert plan.intent.kind == IntentKind.ANNOUNCE
    assert plan.intent.skill_name == "announce"
    assert plan.steps[0].action == "announce_text"
    assert plan.steps[0].parameters["text"] == "openei\u51c6\u5907\u597d\u4e86"


def test_llm_assisted_brain_keeps_deterministic_plan_but_marks_metadata() -> None:
    brain = LLMAssistedSpeechBrain(DeterministicSpeechBrain(dance_action_labels=[]))
    event = PerceptionEvent(
        source="test",
        modality="speech",
        raw_text="\u64ad\u62a5OpenEI",
        normalized_text="\u64ad\u62a5openei",
    )

    plan = brain.plan(event, RuntimeContext(settings=OpenEISettings()))

    assert plan is not None
    assert plan.metadata["brain_mode"] == "llm-assisted"
    assert plan.metadata["llm_assistance"]["status"] == "placeholder"
