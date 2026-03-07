from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

from ..contracts import PerceptionEvent, RuntimeContext, SafetyAction, SkillRequest, TaskPlan
from ..logging import get_logger
from ..ports import Brain, ControlAdapter, FeedbackSink, PerceptionSource, SafetyPolicy
from ..skills.registry import SkillRegistry
from .snapshot import RuntimeSettingsSnapshot, RuntimeSnapshot, RuntimeStateSnapshot

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
        self.context.metadata.setdefault("session_id", uuid4().hex[:12])
        self.context.state.setdefault("event_history", [])
        self.context.state.setdefault("last_result", None)
        self._refresh_runtime_state()

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
        self._record_event(event)
        self._refresh_runtime_state()

        plan = self.brain.plan(event, self.context)
        if plan is None:
            self.context.state["last_result"] = "ignored"
            self._refresh_runtime_state()
            return RuntimeCycleResult(handled=False)

        self.context.state["last_intent"] = plan.intent.kind.value
        self.context.state["last_plan_summary"] = plan.summary
        decision = self.safety.evaluate(event, plan, self.context)

        if decision.clear_pending:
            self.context.pending_plan = None

        if decision.action == SafetyAction.REJECT:
            if decision.feedback_message:
                self.feedback.publish(decision.feedback_message)
            self.context.state["last_result"] = "rejected"
            self._refresh_runtime_state()
            return RuntimeCycleResult(
                handled=True,
                messages=(decision.feedback_message,) if decision.feedback_message else (),
            )

        if decision.action == SafetyAction.CONFIRM:
            self.context.pending_plan = decision.pending_plan or plan
            if decision.feedback_message:
                self.feedback.publish(decision.feedback_message)
            self.context.state["last_result"] = "confirmation-required"
            self._refresh_runtime_state()
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
        self.context.state["last_result"] = "completed" if result.handled else "ignored"
        self._refresh_runtime_state()
        return result

    def stop(self) -> None:
        self._running = False

    def inspect(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            source=self.source.describe(),
            settings=RuntimeSettingsSnapshot.from_settings(self.context.settings),
            state=RuntimeStateSnapshot(
                session_id=str(self.context.metadata.get("session_id", "")),
                history_size=len(self.context.state.get("event_history", [])),
                last_event_text=self.context.state.get("last_event_text"),
                last_intent=self.context.state.get("last_intent"),
                last_plan_summary=self.context.state.get("last_plan_summary"),
                last_result=self.context.state.get("last_result"),
            ),
            skills=self.skills.describe(),
            control=self.control.inspect(),
            pending_plan=self.context.pending_plan.summary if self.context.pending_plan else None,
            event_count=self.context.event_count,
        )

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
                    self.context.state["last_result"] = "control-failure"
                    self._refresh_runtime_state()
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

    def _record_event(self, event: PerceptionEvent) -> None:
        history = self.context.state.setdefault("event_history", [])
        history.append(
            {
                "source": event.source,
                "raw_text": event.raw_text,
                "normalized_text": event.normalized_text,
                "timestamp": event.timestamp,
            }
        )
        if len(history) > 20:
            del history[:-20]
        self.context.state["last_event_text"] = event.raw_text

    def _refresh_runtime_state(self) -> None:
        self.context.state["control"] = self.control.inspect()
        self.context.state["pending_plan"] = self.context.pending_plan.summary if self.context.pending_plan else None
