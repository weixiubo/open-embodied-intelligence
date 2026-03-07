from __future__ import annotations

import os
from dataclasses import dataclass, replace
from enum import StrEnum

from dotenv import load_dotenv


class RuntimeProfile(StrEnum):
    DEMO = "demo"
    DEV = "dev"


class BrainMode(StrEnum):
    DETERMINISTIC = "deterministic"
    LLM_ASSISTED = "llm-assisted"


class InputMode(StrEnum):
    TEXT = "text"
    SCRIPTED = "scripted"
    LIVE_SPEECH = "live-speech"


class TransportMode(StrEnum):
    SIM = "sim"
    AUTO = "auto"
    REAL = "real"


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    stripped = value.strip()
    return stripped or default


def _get_bool(name: str, default: bool) -> bool:
    raw = _get_env(name, "1" if default else "0").lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass(slots=True, frozen=True)
class OpenEISettings:
    profile: RuntimeProfile = RuntimeProfile.DEMO
    brain_mode: BrainMode = BrainMode.DETERMINISTIC
    input_mode: InputMode = InputMode.TEXT
    transport: TransportMode = TransportMode.SIM
    recording_mode: str = "smart_vad"
    confirm_dance_commands: bool = False
    confirm_high_risk_only: bool = True
    startup_greeting: str = "OpenEI runtime is ready."
    text_input_prompt: str = "openei> "
    allow_chat_fallback: bool = True

    @classmethod
    def default_for_profile(cls, profile: RuntimeProfile) -> OpenEISettings:
        if profile == RuntimeProfile.DEV:
            return cls(
                profile=profile,
                brain_mode=BrainMode.DETERMINISTIC,
                confirm_dance_commands=False,
                confirm_high_risk_only=False,
                startup_greeting="OpenEI dev runtime is ready.",
                text_input_prompt="openei-dev> ",
            )

        return cls(
            profile=profile,
            brain_mode=BrainMode.DETERMINISTIC,
            confirm_dance_commands=False,
            confirm_high_risk_only=True,
            startup_greeting="OpenEI demo runtime is ready.",
            text_input_prompt="openei> ",
        )

    @classmethod
    def from_env(cls) -> OpenEISettings:
        load_dotenv()
        profile = RuntimeProfile(_get_env("OPENEI_PROFILE", RuntimeProfile.DEMO.value))
        defaults = cls.default_for_profile(profile)
        return replace(
            defaults,
            brain_mode=BrainMode(_get_env("OPENEI_BRAIN_MODE", defaults.brain_mode.value)),
            input_mode=InputMode(_get_env("OPENEI_INPUT_MODE", defaults.input_mode.value)),
            transport=TransportMode(_get_env("OPENEI_TRANSPORT", defaults.transport.value)),
            recording_mode=_get_env("OPENEI_RECORDING_MODE", defaults.recording_mode),
            confirm_dance_commands=_get_bool(
                "OPENEI_CONFIRM_DANCE_COMMANDS",
                defaults.confirm_dance_commands,
            ),
            confirm_high_risk_only=_get_bool(
                "OPENEI_CONFIRM_HIGH_RISK_ONLY",
                defaults.confirm_high_risk_only,
            ),
            startup_greeting=_get_env("OPENEI_STARTUP_GREETING", defaults.startup_greeting),
            text_input_prompt=_get_env("OPENEI_TEXT_INPUT_PROMPT", defaults.text_input_prompt),
            allow_chat_fallback=_get_bool(
                "OPENEI_ALLOW_CHAT_FALLBACK",
                defaults.allow_chat_fallback,
            ),
        )

    def with_overrides(
        self,
        *,
        profile: RuntimeProfile | None = None,
        brain_mode: BrainMode | None = None,
        input_mode: InputMode | None = None,
        transport: TransportMode | None = None,
        recording_mode: str | None = None,
        confirm_dance_commands: bool | None = None,
        confirm_high_risk_only: bool | None = None,
        startup_greeting: str | None = None,
        text_input_prompt: str | None = None,
        allow_chat_fallback: bool | None = None,
    ) -> OpenEISettings:
        active_profile = profile or self.profile
        if active_profile != self.profile:
            base = self.default_for_profile(active_profile)
            base = replace(
                base,
                brain_mode=self.brain_mode,
                input_mode=self.input_mode,
                transport=self.transport,
                recording_mode=self.recording_mode,
                allow_chat_fallback=self.allow_chat_fallback,
            )
        else:
            base = self

        return replace(
            base,
            profile=active_profile,
            brain_mode=brain_mode or base.brain_mode,
            input_mode=input_mode or base.input_mode,
            transport=transport or base.transport,
            recording_mode=recording_mode or base.recording_mode,
            confirm_dance_commands=(
                base.confirm_dance_commands
                if confirm_dance_commands is None
                else confirm_dance_commands
            ),
            confirm_high_risk_only=(
                base.confirm_high_risk_only
                if confirm_high_risk_only is None
                else confirm_high_risk_only
            ),
            startup_greeting=startup_greeting or base.startup_greeting,
            text_input_prompt=text_input_prompt or base.text_input_prompt,
            allow_chat_fallback=(
                base.allow_chat_fallback
                if allow_chat_fallback is None
                else allow_chat_fallback
            ),
        )
