from __future__ import annotations

from ._legacy_imports import ensure_legacy_project_root_on_path
from ..brain.speech_command import normalize_speech_text
from ..contracts import PerceptionEvent
from ..ports import PerceptionSource


class LegacyLiveSpeechSource(PerceptionSource):
    def __init__(self, recording_mode: str = "smart_vad") -> None:
        ensure_legacy_project_root_on_path()
        from config import RecordingMode as LegacyRecordingMode
        from voice.recording import VoiceRecorder
        from voice.speech_recognition import SpeechRecognizer

        self._recording_mode = LegacyRecordingMode(recording_mode)
        self._recorder = VoiceRecorder()
        self._recognizer = SpeechRecognizer()
        self._exhausted = False

    def describe(self) -> str:
        return f"legacy-live-speech:{self._recording_mode.value}"

    def poll(self) -> PerceptionEvent | None:
        recorded = self._recorder.record(self._recording_mode)
        if not recorded:
            return None

        success, text = self._recognizer.recognize(recorded.payload, recorded.sample_rate)
        if not success or not text:
            return None

        return PerceptionEvent(
            source="legacy-live-speech",
            modality="speech",
            raw_text=text,
            normalized_text=normalize_speech_text(text),
            metadata={"elapsed_seconds": self._recognizer.last_trace.elapsed_seconds},
        )

    def is_exhausted(self) -> bool:
        return self._exhausted
