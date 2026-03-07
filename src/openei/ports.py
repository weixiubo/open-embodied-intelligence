from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .contracts import (
    ControlCommand,
    PerceptionEvent,
    RuntimeContext,
    SafetyDecision,
    SkillRequest,
    SkillResult,
    TaskPlan,
)


class PerceptionSource(ABC):
    @abstractmethod
    def describe(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def poll(self) -> PerceptionEvent | None:
        raise NotImplementedError

    @abstractmethod
    def is_exhausted(self) -> bool:
        raise NotImplementedError

    def close(self) -> None:
        return None


class Brain(ABC):
    @abstractmethod
    def plan(self, event: PerceptionEvent, context: RuntimeContext) -> TaskPlan | None:
        raise NotImplementedError


class SafetyPolicy(ABC):
    @abstractmethod
    def evaluate(
        self,
        event: PerceptionEvent,
        plan: TaskPlan,
        context: RuntimeContext,
    ) -> SafetyDecision:
        raise NotImplementedError


class Skill(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, request: SkillRequest, context: RuntimeContext) -> SkillResult:
        raise NotImplementedError


class ControlAdapter(ABC):
    name: str

    @abstractmethod
    def execute(self, command: ControlCommand, context: RuntimeContext) -> tuple[bool, str]:
        raise NotImplementedError

    @abstractmethod
    def inspect(self) -> dict[str, Any]:
        raise NotImplementedError


class FeedbackSink(ABC):
    @abstractmethod
    def publish(self, message: str) -> None:
        raise NotImplementedError

