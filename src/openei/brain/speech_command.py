from __future__ import annotations

from .deterministic import (
    DeterministicSpeechBrain,
    extract_announcement_text,
    extract_duration_candidates,
    normalize_speech_text,
)

SpeechCommandBrain = DeterministicSpeechBrain

__all__ = [
    "DeterministicSpeechBrain",
    "SpeechCommandBrain",
    "extract_announcement_text",
    "extract_duration_candidates",
    "normalize_speech_text",
]
