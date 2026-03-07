from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from ..brain.speech_command import normalize_speech_text
from ..contracts import PerceptionEvent
from ..ports import PerceptionSource


@dataclass(slots=True)
class ScriptedSpeechSource(PerceptionSource):
    texts: Sequence[str]
    _index: int = 0

    def describe(self) -> str:
        return "scripted-speech"

    def poll(self) -> PerceptionEvent | None:
        if self._index >= len(self.texts):
            return None
        text = self.texts[self._index]
        self._index += 1
        return PerceptionEvent(
            source="scripted-speech",
            modality="speech",
            raw_text=text,
            normalized_text=normalize_speech_text(text),
        )

    def is_exhausted(self) -> bool:
        return self._index >= len(self.texts)


@dataclass(slots=True)
class InteractiveSpeechTextSource(PerceptionSource):
    prompt: str = "openei> "
    _exhausted: bool = False
    _history: list[str] = field(default_factory=list)

    def describe(self) -> str:
        return "interactive-text-speech"

    def poll(self) -> PerceptionEvent | None:
        if self._exhausted:
            return None
        try:
            text = input(self.prompt).strip()
        except EOFError:
            self._exhausted = True
            return None
        if not text:
            return None
        self._history.append(text)
        return PerceptionEvent(
            source="interactive-text",
            modality="speech",
            raw_text=text,
            normalized_text=normalize_speech_text(text),
        )

    def is_exhausted(self) -> bool:
        return self._exhausted

