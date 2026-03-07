from __future__ import annotations

from openei.config import OpenEISettings
from openei.contracts import (
    ControlCommand,
    IntentKind,
    PerceptionEvent,
    RuntimeContext,
    SafetyAction,
    SafetyDecision,
    SkillRequest,
    SkillResult,
    StructuredIntent,
    TaskPlan,
    TaskStep,
)
from openei.feedback import MemoryFeedbackSink
from openei.ports import Brain, ControlAdapter, FeedbackSink, PerceptionSource, SafetyPolicy, Skill
from openei.runtime.engine import OpenEIRuntime
from openei.skills.registry import SkillRegistry


class FakeSource(PerceptionSource):
    def __init__(self) -> None:
        self._done = False

    def describe(self) -> str:
        return "fake"

    def poll(self) -> PerceptionEvent | None:
        if self._done:
            return None
        self._done = True
        return PerceptionEvent(source="fake", modality="speech", raw_text="hello", normalized_text="hello")

    def is_exhausted(self) -> bool:
        return self._done


class FakeBrain(Brain):
    def plan(self, event: PerceptionEvent, context: RuntimeContext) -> TaskPlan | None:
        intent = StructuredIntent(
            kind=IntentKind.ACTION,
            skill_name="fake",
            raw_text=event.raw_text,
            normalized_text=event.normalized_text,
        )
        return TaskPlan(
            intent=intent,
            steps=(TaskStep(skill_name="fake", action="emit"),),
            summary="fake action",
        )


class FakeSafety(SafetyPolicy):
    def evaluate(self, event: PerceptionEvent, plan: TaskPlan, context: RuntimeContext) -> SafetyDecision:
        return SafetyDecision(action=SafetyAction.ALLOW, reason="ok", plan=plan)


class FakeSkill(Skill):
    name = "fake"
    description = "fake"

    def execute(self, request: SkillRequest, context: RuntimeContext) -> SkillResult:
        return SkillResult(
            success=True,
            emitted_commands=(ControlCommand(adapter="fake", command_type="noop"),),
        )


class FakeControl(ControlAdapter):
    name = "fake"

    def __init__(self) -> None:
        self.executed = []

    def execute(self, command: ControlCommand, context: RuntimeContext) -> tuple[bool, str]:
        self.executed.append(command.command_type)
        return True, "ok"

    def inspect(self) -> dict[str, object]:
        return {"mode": "fake", "executed": len(self.executed)}


def test_runtime_accepts_custom_ports_without_legacy_dependencies() -> None:
    registry = SkillRegistry()
    registry.register(FakeSkill())
    control = FakeControl()
    feedback: FeedbackSink = MemoryFeedbackSink()
    runtime = OpenEIRuntime(
        source=FakeSource(),
        brain=FakeBrain(),
        safety=FakeSafety(),
        skills=registry,
        control=control,
        feedback=feedback,
        context=RuntimeContext(settings=OpenEISettings()),
    )

    runtime.run(once=True)

    assert control.executed == ["noop"]

