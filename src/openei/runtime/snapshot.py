from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import OpenEISettings
from ..skills.registry import SkillDescriptor


@dataclass(frozen=True, slots=True)
class RuntimeSettingsSnapshot:
    profile: str
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
            "input_mode": self.input_mode,
            "transport": self.transport,
            "recording_mode": self.recording_mode,
            "confirm_dance_commands": self.confirm_dance_commands,
            "confirm_high_risk_only": self.confirm_high_risk_only,
            "allow_chat_fallback": self.allow_chat_fallback,
        }


@dataclass(frozen=True, slots=True)
class RuntimeSnapshot:
    source: str
    settings: RuntimeSettingsSnapshot
    skills: tuple[SkillDescriptor, ...]
    control: dict[str, object]
    pending_plan: str | None
    event_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "settings": self.settings.to_dict(),
            "skills": [descriptor.to_dict() for descriptor in self.skills],
            "control": self.control,
            "pending_plan": self.pending_plan,
            "event_count": self.event_count,
        }
