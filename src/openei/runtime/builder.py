from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..brain.speech_command import SpeechCommandBrain
from ..config import InputMode, OpenEISettings, TransportMode
from ..contracts import RuntimeContext
from ..feedback import ConsoleFeedbackSink
from ..logging import configure_logging
from ..perception.sources import InteractiveSpeechTextSource, ScriptedSpeechSource
from ..ports import ControlAdapter, PerceptionSource
from ..safety.default import DefaultSafetyPolicy
from ..skills.dance import DanceCatalog, DanceSkill
from ..skills.registry import SkillRegistry
from ..skills.system import SystemSkill
from .engine import OpenEIRuntime


@dataclass(slots=True)
class RuntimeBundle:
    settings: OpenEISettings
    runtime: OpenEIRuntime
    skills: SkillRegistry
    control_name: str


def build_runtime_bundle(
    settings: OpenEISettings | None = None,
    scripted_inputs: Sequence[str] | None = None,
) -> RuntimeBundle:
    configure_logging()
    active_settings = settings or OpenEISettings.from_env()
    source = _build_source(active_settings, scripted_inputs or ())
    catalog = _build_dance_catalog()
    control = _build_control(active_settings)

    registry = SkillRegistry()
    registry.register(SystemSkill(control=control))
    registry.register(DanceSkill(catalog=catalog))

    brain = SpeechCommandBrain(dance_action_labels=catalog.action_labels())
    safety = DefaultSafetyPolicy(
        confirm_dance_commands=active_settings.confirm_dance_commands,
        confirm_high_risk_only=active_settings.confirm_high_risk_only,
    )
    context = RuntimeContext(settings=active_settings)
    feedback = ConsoleFeedbackSink()
    runtime = OpenEIRuntime(
        source=source,
        brain=brain,
        safety=safety,
        skills=registry,
        control=control,
        feedback=feedback,
        context=context,
    )
    return RuntimeBundle(settings=active_settings, runtime=runtime, skills=registry, control_name=control.name)


def _build_source(settings: OpenEISettings, scripted_inputs: Sequence[str]) -> PerceptionSource:
    if settings.input_mode == InputMode.SCRIPTED:
        return ScriptedSpeechSource(texts=scripted_inputs)
    if settings.input_mode == InputMode.LIVE_SPEECH:
        from ..adapters.legacy_speech import LegacyLiveSpeechSource

        return LegacyLiveSpeechSource(recording_mode=settings.recording_mode)
    return InteractiveSpeechTextSource(prompt=settings.text_input_prompt)


def _build_dance_catalog() -> DanceCatalog:
    from ..adapters.legacy_dance import LegacyDanceCatalog

    return LegacyDanceCatalog()


def _build_control(settings: OpenEISettings) -> ControlAdapter:
    if settings.transport == TransportMode.SIM:
        from ..control.simulation import SimulationControlAdapter

        return SimulationControlAdapter()

    from ..adapters.legacy_dance import LegacyDanceControlAdapter

    return LegacyDanceControlAdapter(settings.transport)
