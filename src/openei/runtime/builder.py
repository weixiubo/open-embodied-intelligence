from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..brain import DeterministicSpeechBrain, LLMAssistedSpeechBrain
from ..config import BrainMode, InputMode, OpenEISettings, TransportMode
from ..contracts import RuntimeContext
from ..feedback import ConsoleFeedbackSink
from ..logging import configure_logging
from ..perception.sources import InteractiveSpeechTextSource, ScriptedSpeechSource
from ..ports import Brain, ControlAdapter, PerceptionSource
from ..safety.default import DefaultSafetyPolicy
from ..skills import build_builtin_skills
from ..skills.dance import DanceCatalog
from ..skills.registry import SkillRegistry
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
    registry.register_many(
        build_builtin_skills(
            dance_catalog=catalog,
            control=control,
        )
    )

    brain = _build_brain(active_settings, catalog)
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


def _build_brain(settings: OpenEISettings, catalog: DanceCatalog) -> Brain:
    deterministic = DeterministicSpeechBrain(dance_action_labels=catalog.action_labels())
    if settings.brain_mode == BrainMode.LLM_ASSISTED:
        return LLMAssistedSpeechBrain(deterministic)
    return deterministic


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
