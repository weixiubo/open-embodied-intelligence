from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import PerceptionEvent, RuntimeContext, SafetyAction, SkillRequest, TaskPlan
from ..logging import get_logger
from ..ports import Brain, ControlAdapter, FeedbackSink, PerceptionSource, SafetyPolicy
from ..skills.registry import SkillRegistry

logger = get_logger("runtime")


@dataclass(slots=True)
class RuntimeCycleResult:
    handled: bool
    messages: tuple[str, ...] = ()
    should_exit: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


class OpenEIRuntime:
    def __init__(
        self,
        source: PerceptionSource,
        brain: Brain,
        safety: SafetyPolicy,
        skills: SkillRegistry,
        control: ControlAdapter,
        feedback: FeedbackSink,
        context: RuntimeContext,
    ) -> None:
        self.source = source
        self.brain = brain
        self.safety = safety
        self.skills = skills
        self.control = control
        self.feedback = feedback
        self.context = context
        self._running = False

    def run(self, once: bool = False, max_events: int | None = None) -> int:
        self._running = True
        self.feedback.publish(self.context.settings.startup_greeting)
        processed = 0

        try:
            while self._running:
                event = self.source.poll()
                if event is None:
                    if once or self.source.is_exhausted():
                        break
                    continue

                processed += 1
                result = self.handle_event(event)
                if result.should_exit:
                    break
                if once:
                    break
                if max_events is not None and processed >= max_events:
                    break
        finally:
            self.source.close()
            self._running = False
        return 0

    def handle_event(self, event: PerceptionEvent) -> RuntimeCycleResult:
        self.context.event_count += 1
        plan = self.brain.plan(event, self.context)
        if plan is None:
            return RuntimeCycleResult(handled=False)

        decision = self.safety.evaluate(event, plan, self.context)

        if decision.clear_pending:
            self.context.pending_plan = None

        if decision.action == SafetyAction.REJECT:
            if decision.feedback_message:
                self.feedback.publish(decision.feedback_message)
            return RuntimeCycleResult(
                handled=True,
                messages=(decision.feedback_message,) if decision.feedback_message else (),
            )

        if decision.action == SafetyAction.CONFIRM:
            self.context.pending_plan = decision.pending_plan or plan
            if decision.feedback_message:
                self.feedback.publish(decision.feedback_message)
            return RuntimeCycleResult(
                handled=True,
                messages=(decision.feedback_message,) if decision.feedback_message else (),
                metadata={"pending": True},
            )

        active_plan = decision.plan or plan
        pre_messages: list[str] = []
        if decision.feedback_message:
            self.feedback.publish(decision.feedback_message)
            pre_messages.append(decision.feedback_message)
        result = self._execute_plan(event, active_plan)
        if pre_messages:
            result.messages = tuple(pre_messages) + result.messages
        return result

    def stop(self) -> None:
        self._running = False

    def inspect(self) -> dict[str, object]:
        return {
            "source": self.source.describe(),
            "settings": {
                "input_mode": self.context.settings.input_mode.value,
                "transport": self.context.settings.transport.value,
                "recording_mode": self.context.settings.recording_mode,
                "confirm_dance_commands": self.context.settings.confirm_dance_commands,
                "confirm_high_risk_only": self.context.settings.confirm_high_risk_only,
            },
            "skills": [descriptor["name"] for descriptor in self.skills.describe()],
            "control": self.control.inspect(),
            "pending_plan": self.context.pending_plan.summary if self.context.pending_plan else None,
        }

    def _execute_plan(self, event: PerceptionEvent, plan: TaskPlan) -> RuntimeCycleResult:
        messages: list[str] = []
        should_exit = False

        for step in plan.steps:
            skill = self.skills.get(step.skill_name)
            if skill is None:
                message = f"Skill '{step.skill_name}' is not registered."
                self.feedback.publish(message)
                return RuntimeCycleResult(handled=True, messages=(message,))

            request = SkillRequest(event=event, intent=plan.intent, plan=plan, step=step)
            result = skill.execute(request, self.context)
            self._publish_messages(result.messages, messages)
            should_exit = should_exit or result.should_exit

            for command in result.emitted_commands:
                ok, control_message = self.control.execute(command, self.context)
                if control_message:
                    self.feedback.publish(control_message)
                    messages.append(control_message)
                if not ok:
                    return RuntimeCycleResult(
                        handled=True,
                        messages=tuple(messages),
                        should_exit=should_exit,
                    )

        return RuntimeCycleResult(handled=True, messages=tuple(messages), should_exit=should_exit)

    def _publish_messages(self, new_messages: tuple[str, ...], collector: list[str]) -> None:
        for message in new_messages:
            self.feedback.publish(message)
            collector.append(message)
