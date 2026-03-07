from __future__ import annotations

from dataclasses import dataclass

from ..contracts import (
    IntentKind,
    PerceptionEvent,
    RuntimeContext,
    SafetyAction,
    SafetyDecision,
    TaskPlan,
)
from ..ports import SafetyPolicy


@dataclass(frozen=True, slots=True)
class SafetyRules:
    min_dance_seconds: int = 5
    max_dance_seconds: int = 60
    reject_start_while_dancing: bool = True
    reject_action_while_dancing: bool = True
    reject_stop_when_idle: bool = False


class DefaultSafetyPolicy(SafetyPolicy):
    def __init__(
        self,
        confirm_dance_commands: bool,
        confirm_high_risk_only: bool,
        rules: SafetyRules | None = None,
    ) -> None:
        self.confirm_dance_commands = confirm_dance_commands
        self.confirm_high_risk_only = confirm_high_risk_only
        self.rules = rules or SafetyRules()

    def evaluate(
        self,
        event: PerceptionEvent,
        plan: TaskPlan,
        context: RuntimeContext,
    ) -> SafetyDecision:
        intent = plan.intent
        control_state = context.state.get("control", {})
        is_dancing = bool(control_state.get("is_dancing"))

        if context.pending_plan is not None:
            if intent.kind == IntentKind.CONFIRM:
                pending = context.pending_plan
                return SafetyDecision(
                    action=SafetyAction.ALLOW,
                    reason="confirmed_pending_plan",
                    plan=pending,
                    feedback_message=f"Confirmed: {pending.summary}",
                    clear_pending=True,
                )
            if intent.kind == IntentKind.CANCEL:
                return SafetyDecision(
                    action=SafetyAction.REJECT,
                    reason="cancelled_pending_plan",
                    feedback_message="Pending request cancelled.",
                    clear_pending=True,
                )
            return SafetyDecision(
                action=SafetyAction.REJECT,
                reason="pending_confirmation_exists",
                feedback_message="There is already a pending confirmation. Confirm or cancel it first.",
            )

        if intent.kind in {IntentKind.CONFIRM, IntentKind.CANCEL}:
            return SafetyDecision(
                action=SafetyAction.REJECT,
                reason="no_pending_plan",
                feedback_message="There is no pending request to confirm or cancel.",
            )

        if intent.kind == IntentKind.DANCE:
            duration = intent.parameters.get("duration_seconds")
            if duration is None:
                return SafetyDecision(
                    action=SafetyAction.REJECT,
                    reason="missing_duration",
                    feedback_message="Specify a dance duration, for example 'dance 10 seconds'.",
                )
            if duration < self.rules.min_dance_seconds or duration > self.rules.max_dance_seconds:
                return SafetyDecision(
                    action=SafetyAction.REJECT,
                    reason="duration_out_of_range",
                    feedback_message=(
                        f"Dance duration must stay between {self.rules.min_dance_seconds} and "
                        f"{self.rules.max_dance_seconds} seconds."
                    ),
                )
            if is_dancing and self.rules.reject_start_while_dancing:
                return SafetyDecision(
                    action=SafetyAction.REJECT,
                    reason="already_dancing",
                    feedback_message="The robot is already dancing. Stop it before starting a new dance task.",
                )
            needs_confirmation = self.confirm_dance_commands or (
                self.confirm_high_risk_only and intent.is_high_risk
            )
            if needs_confirmation:
                return SafetyDecision(
                    action=SafetyAction.CONFIRM,
                    reason="dance_requires_confirmation",
                    feedback_message=f"Please confirm: {plan.summary}",
                    pending_plan=plan,
                )

        if intent.kind == IntentKind.ACTION and is_dancing and self.rules.reject_action_while_dancing:
            return SafetyDecision(
                action=SafetyAction.REJECT,
                reason="action_blocked_while_dancing",
                feedback_message="Single-action execution is blocked while the robot is dancing.",
            )

        if intent.kind == IntentKind.STOP and not is_dancing and self.rules.reject_stop_when_idle:
            return SafetyDecision(
                action=SafetyAction.REJECT,
                reason="stop_when_idle",
                feedback_message="The robot is already idle.",
            )

        return SafetyDecision(action=SafetyAction.ALLOW, reason="allowed", plan=plan)
