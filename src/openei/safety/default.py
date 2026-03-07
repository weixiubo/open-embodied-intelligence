from __future__ import annotations

from ..contracts import (
    IntentKind,
    PerceptionEvent,
    RuntimeContext,
    SafetyAction,
    SafetyDecision,
    TaskPlan,
)
from ..ports import SafetyPolicy


class DefaultSafetyPolicy(SafetyPolicy):
    def __init__(self, confirm_dance_commands: bool, confirm_high_risk_only: bool) -> None:
        self.confirm_dance_commands = confirm_dance_commands
        self.confirm_high_risk_only = confirm_high_risk_only

    def evaluate(
        self,
        event: PerceptionEvent,
        plan: TaskPlan,
        context: RuntimeContext,
    ) -> SafetyDecision:
        intent = plan.intent

        if context.pending_plan is not None:
            if intent.kind == IntentKind.CONFIRM:
                pending = context.pending_plan
                return SafetyDecision(
                    action=SafetyAction.ALLOW,
                    reason="confirmed_pending_plan",
                    plan=pending,
                    feedback_message=f"确认执行：{pending.summary}",
                    clear_pending=True,
                )
            if intent.kind == IntentKind.CANCEL:
                return SafetyDecision(
                    action=SafetyAction.REJECT,
                    reason="cancelled_pending_plan",
                    feedback_message="已取消待确认任务。",
                    clear_pending=True,
                )
            return SafetyDecision(
                action=SafetyAction.REJECT,
                reason="pending_confirmation_exists",
                feedback_message="当前有待确认任务，请先确认或取消。",
            )

        if intent.kind in {IntentKind.CONFIRM, IntentKind.CANCEL}:
            return SafetyDecision(
                action=SafetyAction.REJECT,
                reason="no_pending_plan",
                feedback_message="当前没有待确认任务。",
            )

        if intent.kind == IntentKind.DANCE:
            duration = intent.parameters.get("duration_seconds")
            if duration is None:
                return SafetyDecision(
                    action=SafetyAction.REJECT,
                    reason="missing_duration",
                    feedback_message="请明确说明跳舞时长，例如“跳舞十秒”。",
                )
            if duration < 5 or duration > 60:
                return SafetyDecision(
                    action=SafetyAction.REJECT,
                    reason="duration_out_of_range",
                    feedback_message="跳舞时长必须在 5 到 60 秒之间。",
                )
            needs_confirmation = self.confirm_dance_commands or (
                self.confirm_high_risk_only and intent.is_high_risk
            )
            if needs_confirmation:
                return SafetyDecision(
                    action=SafetyAction.CONFIRM,
                    reason="dance_requires_confirmation",
                    feedback_message=f"请确认，是否执行 {plan.summary}？",
                    pending_plan=plan,
                )

        return SafetyDecision(action=SafetyAction.ALLOW, reason="allowed", plan=plan)
