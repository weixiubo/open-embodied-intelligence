from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import OpenEISettings
from ..skills.registry import SkillDescriptor


@dataclass(frozen=True, slots=True)
class RuntimeSettingsSnapshot:
    profile: str
    brain_mode: str
    input_mode: str
    transport: str
    recording_mode: str
    confirm_dance_commands: bool
    confirm_high_risk_only: bool
    allow_chat_fallback: bool

    @classmethod
    def from_settings(cls, settings: OpenEISettings) -> RuntimeSettingsSnapshot:
        return cls(
            profile=settings.profile.value,
            brain_mode=settings.brain_mode.value,
            input_mode=settings.input_mode.value,
            transport=settings.transport.value,
            recording_mode=settings.recording_mode,
            confirm_dance_commands=settings.confirm_dance_commands,
            confirm_high_risk_only=settings.confirm_high_risk_only,
            allow_chat_fallback=settings.allow_chat_fallback,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "brain_mode": self.brain_mode,
            "input_mode": self.input_mode,
            "transport": self.transport,
            "recording_mode": self.recording_mode,
            "confirm_dance_commands": self.confirm_dance_commands,
            "confirm_high_risk_only": self.confirm_high_risk_only,
            "allow_chat_fallback": self.allow_chat_fallback,
        }


@dataclass(frozen=True, slots=True)
class RuntimeStateSnapshot:
    session_id: str
    history_size: int
    last_event_text: str | None
    last_intent: str | None
    last_plan_summary: str | None
    last_result: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "history_size": self.history_size,
            "last_event_text": self.last_event_text,
            "last_intent": self.last_intent,
            "last_plan_summary": self.last_plan_summary,
            "last_result": self.last_result,
        }


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    source: str
    settings: RuntimeSettingsSnapshot
    state: RuntimeStateSnapshot
    skills: tuple[SkillDescriptor, ...]
    control: dict[str, object]
    pending_plan: str | None
    event_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "settings": self.settings.to_dict(),
            "state": self.state.to_dict(),
            "skills": [descriptor.to_dict() for descriptor in self.skills],
            "control": self.control,
            "pending_plan": self.pending_plan,
            "event_count": self.event_count,
        }
