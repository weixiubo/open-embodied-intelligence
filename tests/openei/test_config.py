from __future__ import annotations

from openei.config import BrainMode, InputMode, OpenEISettings, RuntimeProfile, TransportMode


def test_demo_profile_defaults_to_high_risk_confirmation() -> None:
    settings = OpenEISettings.default_for_profile(RuntimeProfile.DEMO)

    assert settings.profile == RuntimeProfile.DEMO
    assert settings.brain_mode == BrainMode.DETERMINISTIC
    assert settings.confirm_high_risk_only is True
    assert settings.text_input_prompt == "openei> "


def test_dev_profile_can_be_overridden_without_losing_profile_identity() -> None:
    settings = OpenEISettings.default_for_profile(RuntimeProfile.DEV).with_overrides(
        brain_mode=BrainMode.LLM_ASSISTED,
        input_mode=InputMode.SCRIPTED,
        transport=TransportMode.SIM,
    )

    assert settings.profile == RuntimeProfile.DEV
    assert settings.brain_mode == BrainMode.LLM_ASSISTED
    assert settings.input_mode == InputMode.SCRIPTED
    assert settings.transport == TransportMode.SIM
    assert settings.confirm_high_risk_only is False
