from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum

from dotenv import load_dotenv


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
    input_mode: InputMode = InputMode.TEXT
    transport: TransportMode = TransportMode.SIM
    recording_mode: str = "smart_vad"
    confirm_dance_commands: bool = False
    confirm_high_risk_only: bool = True
    startup_greeting: str = "OpenEI runtime is ready."
    text_input_prompt: str = "openei> "
    allow_chat_fallback: bool = True

    @classmethod
    def from_env(cls) -> OpenEISettings:
        load_dotenv()
        return cls(
            input_mode=InputMode(_get_env("OPENEI_INPUT_MODE", InputMode.TEXT.value)),
            transport=TransportMode(_get_env("OPENEI_TRANSPORT", TransportMode.SIM.value)),
            recording_mode=_get_env("OPENEI_RECORDING_MODE", "smart_vad"),
            confirm_dance_commands=_get_bool("OPENEI_CONFIRM_DANCE_COMMANDS", False),
            confirm_high_risk_only=_get_bool("OPENEI_CONFIRM_HIGH_RISK_ONLY", True),
            startup_greeting=_get_env("OPENEI_STARTUP_GREETING", "OpenEI runtime is ready."),
            text_input_prompt=_get_env("OPENEI_TEXT_INPUT_PROMPT", "openei> "),
            allow_chat_fallback=_get_bool("OPENEI_ALLOW_CHAT_FALLBACK", True),
        )
