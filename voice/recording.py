"""
录音与简单 VAD。
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional

from config import RecordingMode, audio_config
from utils.helpers import RollingWindow
from utils.logger import logger

try:
    import numpy as np
    import pyaudio

    PYAUDIO_AVAILABLE = True
except ImportError:
    np = None
    pyaudio = None
    PYAUDIO_AVAILABLE = False


@dataclass
class RecordedAudio:
    payload: bytes
    sample_rate: int
    duration_seconds: float
    mode: RecordingMode


class VoiceRecorder:
    """统一录音入口。"""

    def __init__(self) -> None:
        self.recording_config = audio_config.recording
        self.vad_config = audio_config.vad
        self.paused = False

    @property
    def is_available(self) -> bool:
        return PYAUDIO_AVAILABLE

    def pause(self) -> None:
        self.paused = True

    def resume(self) -> None:
        self.paused = False

    def record(self, mode: RecordingMode) -> Optional[RecordedAudio]:
        if not self.is_available:
            logger.error("pyaudio 不可用，无法录音")
            return None

        if mode == RecordingMode.FIXED_DURATION:
            return self._record_fixed_duration(self.recording_config.fixed_duration_seconds)
        if mode == RecordingMode.PUSH_TO_TALK:
            return self._record_push_to_talk()
        return self._record_smart_vad()

    def _open_stream(self):
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=self.recording_config.channels,
            rate=self.recording_config.sample_rate,
            input=True,
            frames_per_buffer=self.recording_config.chunk_size,
        )
        return audio, stream

    def _record_fixed_duration(self, duration_seconds: float) -> Optional[RecordedAudio]:
        audio, stream = self._open_stream()
        frames = []
        chunks = int(
            self.recording_config.sample_rate / self.recording_config.chunk_size * duration_seconds
        )
        try:
            for _ in range(chunks):
                if self.paused:
                    time.sleep(0.05)
                    continue
                frames.append(stream.read(self.recording_config.chunk_size, exception_on_overflow=False))
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

        payload = b"".join(frames)
        return RecordedAudio(
            payload=payload,
            sample_rate=self.recording_config.sample_rate,
            duration_seconds=duration_seconds,
            mode=RecordingMode.FIXED_DURATION,
        )

    def _record_push_to_talk(self) -> Optional[RecordedAudio]:
        logger.info("按回车开始录音，再按回车结束录音。")
        try:
            input()
        except EOFError:
            logger.warning("当前环境无法读取回车输入，改用固定时长录音")
            return self._record_fixed_duration(self.recording_config.fixed_duration_seconds)

        audio, stream = self._open_stream()
        stop_event = threading.Event()
        frames = []

        def _wait_for_stop() -> None:
            try:
                input()
            except EOFError:
                pass
            stop_event.set()

        stopper = threading.Thread(target=_wait_for_stop, daemon=True)
        stopper.start()
        start_time = time.time()
        try:
            while not stop_event.is_set():
                if self.paused:
                    time.sleep(0.05)
                    continue
                if time.time() - start_time >= self.recording_config.max_recording_duration:
                    break
                frames.append(stream.read(self.recording_config.chunk_size, exception_on_overflow=False))
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

        duration = time.time() - start_time
        if not frames:
            return None
        return RecordedAudio(
            payload=b"".join(frames),
            sample_rate=self.recording_config.sample_rate,
            duration_seconds=duration,
            mode=RecordingMode.PUSH_TO_TALK,
        )

    def _record_smart_vad(self) -> Optional[RecordedAudio]:
        audio, stream = self._open_stream()
        pre_buffer = deque(maxlen=self.recording_config.pre_speech_frames)
        noise_window = RollingWindow(maxlen=self.vad_config.noise_adaptation_frames)
        frames = []
        detection_count = 0
        silence_count = 0
        started = False
        start_time = time.time()
        speech_start_time: Optional[float] = None

        calibration_chunks = max(
            1,
            int(
                self.recording_config.sample_rate
                / self.recording_config.chunk_size
                * self.recording_config.calibration_seconds
            ),
        )

        try:
            for index in range(
                int(
                    self.recording_config.sample_rate
                    / self.recording_config.chunk_size
                    * self.recording_config.max_recording_duration
                )
            ):
                if self.paused:
                    time.sleep(0.05)
                    continue

                data = stream.read(self.recording_config.chunk_size, exception_on_overflow=False)
                audio_array = np.frombuffer(data, dtype=np.int16)
                volume = float(np.sqrt(np.mean(audio_array.astype(np.float32) ** 2)))
                pre_buffer.append(data)

                if index < calibration_chunks:
                    noise_window.append(volume)
                    continue

                dynamic_threshold = self.vad_config.volume_threshold
                if self.vad_config.enable_noise_adaptation and len(noise_window):
                    dynamic_threshold = max(
                        dynamic_threshold,
                        noise_window.mean() * self.vad_config.noise_multiplier,
                    )

                is_speech = volume >= dynamic_threshold

                if not started:
                    if not is_speech:
                        noise_window.append(volume)
                    if is_speech:
                        detection_count += 1
                    else:
                        detection_count = 0

                    if detection_count >= self.vad_config.detection_frames:
                        started = True
                        speech_start_time = time.time()
                        frames.extend(list(pre_buffer))
                        logger.info("检测到语音开始，进入录音状态")
                    continue

                frames.append(data)
                if is_speech:
                    silence_count = 0
                else:
                    silence_count += 1

                elapsed = (time.time() - speech_start_time) if speech_start_time else 0.0
                if (
                    silence_count >= self.vad_config.silence_frames_limit
                    and elapsed >= self.vad_config.min_speech_duration
                ):
                    logger.info("检测到语音结束，停止录音")
                    break
                if elapsed >= self.vad_config.max_speech_duration:
                    logger.info("达到语音录音上限，停止录音")
                    break
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()

        if not started or not frames:
            return None

        duration = time.time() - (speech_start_time or start_time)
        if duration < self.vad_config.min_speech_duration:
            return None

        return RecordedAudio(
            payload=b"".join(frames),
            sample_rate=self.recording_config.sample_rate,
            duration_seconds=duration,
            mode=RecordingMode.SMART_VAD,
        )
