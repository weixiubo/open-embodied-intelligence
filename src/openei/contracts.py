from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .config import OpenEISettings


class IntentKind(StrEnum):
    DANCE = "dance"
    STOP = "stop"
    ACTION = "action"
    LIST_ACTIONS = "list_actions"
    STATUS = "status"
    EXIT = "exit"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    CHAT = "chat"
    UNKNOWN = "unknown"


class SafetyAction(StrEnum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    REJECT = "reject"
    MODIFY = "modify"


@dataclass(slots=True)
class PerceptionEvent:
    source: str
    modality: str
    raw_text: str
    normalized_text: str
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class StructuredIntent:
    kind: IntentKind
    skill_name: str | None
    raw_text: str
    normalized_text: str
    parameters: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    risk_flags: tuple[str, ...] = ()
    delegation_hints: tuple[str, ...] = ()

    @property
    def is_high_risk(self) -> bool:
        return bool(self.risk_flags)


@dataclass(slots=True)
class TaskStep:
    skill_name: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    delegation_target: str | None = None


@dataclass(slots=True)
class TaskPlan:
    intent: StructuredIntent
    steps: tuple[TaskStep, ...]
    summary: str
    delegation_enabled: bool = False
    delegation_candidates: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SafetyDecision:
    action: SafetyAction
    reason: str
    plan: TaskPlan | None = None
    feedback_message: str = ""
    pending_plan: TaskPlan | None = None
    clear_pending: bool = False


@dataclass(slots=True)
class ControlCommand:
    adapter: str
    command_type: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SkillRequest:
    event: PerceptionEvent
    intent: StructuredIntent
    plan: TaskPlan
    step: TaskStep


@dataclass(slots=True)
class SkillResult:
    success: bool
    messages: tuple[str, ...] = ()
    emitted_commands: tuple[ControlCommand, ...] = ()
    should_exit: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeContext:
    settings: OpenEISettings
    pending_plan: TaskPlan | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    event_count: int = 0

