from __future__ import annotations

from openei.brain.speech_command import SpeechCommandBrain
from openei.config import OpenEISettings
from openei.contracts import PerceptionEvent, RuntimeContext, SafetyAction
from openei.safety.default import DefaultSafetyPolicy, SafetyRules


def _plan_from_text(text: str):
    brain = SpeechCommandBrain(dance_action_labels=["\u6325\u624b"])
    event = PerceptionEvent(source="test", modality="speech", raw_text=text, normalized_text=text)
    context = RuntimeContext(settings=OpenEISettings())
    context.state["control"] = {"is_dancing": False}
    plan = brain.plan(event, context)
    assert plan is not None
    return event, plan, context


def test_safety_confirms_high_risk_dance() -> None:
    event, plan, context = _plan_from_text("\u8df3\u821e50\u79d2")
    policy = DefaultSafetyPolicy(confirm_dance_commands=False, confirm_high_risk_only=True)

    decision = policy.evaluate(event, plan, context)

    assert decision.action == SafetyAction.CONFIRM
    assert decision.pending_plan is not None
    assert "Please confirm:" in decision.feedback_message


def test_safety_rejects_missing_duration() -> None:
    event, plan, context = _plan_from_text("\u8df3\u821e")
    policy = DefaultSafetyPolicy(confirm_dance_commands=False, confirm_high_risk_only=True)

    decision = policy.evaluate(event, plan, context)

    assert decision.action == SafetyAction.REJECT
    assert decision.reason == "missing_duration"


def test_safety_handles_confirm_and_cancel_for_pending_plan() -> None:
    brain = SpeechCommandBrain(dance_action_labels=["\u6325\u624b"])
    settings = OpenEISettings()
    context = RuntimeContext(settings=settings)
    context.state["control"] = {"is_dancing": False}
    policy = DefaultSafetyPolicy(confirm_dance_commands=False, confirm_high_risk_only=True)

    event = PerceptionEvent(source="test", modality="speech", raw_text="\u8df3\u821e50\u79d2", normalized_text="\u8df3\u821e50\u79d2")
    pending_plan = brain.plan(event, context)
    assert pending_plan is not None
    context.pending_plan = pending_plan

    confirm_event = PerceptionEvent(source="test", modality="speech", raw_text="\u786e\u8ba4", normalized_text="\u786e\u8ba4")
    confirm_plan = brain.plan(confirm_event, context)
    assert confirm_plan is not None

    confirm_decision = policy.evaluate(confirm_event, confirm_plan, context)
    assert confirm_decision.action == SafetyAction.ALLOW
    assert confirm_decision.clear_pending is True
    assert confirm_decision.plan is pending_plan

    context.pending_plan = pending_plan
    cancel_event = PerceptionEvent(source="test", modality="speech", raw_text="\u53d6\u6d88", normalized_text="\u53d6\u6d88")
    cancel_plan = brain.plan(cancel_event, context)
    assert cancel_plan is not None

    cancel_decision = policy.evaluate(cancel_event, cancel_plan, context)
    assert cancel_decision.action == SafetyAction.REJECT
    assert cancel_decision.clear_pending is True


def test_safety_rejects_new_dance_when_robot_is_already_dancing() -> None:
    event, plan, context = _plan_from_text("\u8df3\u821e10\u79d2")
    context.state["control"] = {"is_dancing": True}
    policy = DefaultSafetyPolicy(
        confirm_dance_commands=False,
        confirm_high_risk_only=True,
        rules=SafetyRules(reject_start_while_dancing=True),
    )

    decision = policy.evaluate(event, plan, context)

    assert decision.action == SafetyAction.REJECT
    assert decision.reason == "already_dancing"
