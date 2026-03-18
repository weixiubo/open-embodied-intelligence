"""
音频配置模块。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AudioRecordingConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_size: int = 1024
    format_bits: int = 16
    fixed_duration_seconds: float = 4.0
    max_recording_duration: float = 15.0
    calibration_seconds: float = 0.5
    pre_speech_frames: int = 4
    # 指定麦克风设备索引（None = 系统默认）。可通过 AUDIO_INPUT_DEVICE_INDEX 环境变量覆盖。
    # 优先级低于 AUDIO_INPUT_DEVICE_NAME（名称匹配）。
    input_device_index: Optional[int] = field(default=None, repr=True)
    # 按设备名称关键字匹配麦克风（推荐，不受插拔顺序影响）。
    # 填写 arecord -l 输出中的设备名片段，如 "USB2.0" 或 "USB PnP"。
    # 可通过 AUDIO_INPUT_DEVICE_NAME 环境变量设置。
    input_device_name: Optional[str] = field(default=None, repr=True)

    def __post_init__(self) -> None:
        _sr = os.getenv("AUDIO_SAMPLE_RATE")
        if _sr is not None:
            try:
                self.sample_rate = int(_sr)
            except ValueError:
                pass
        _name = os.getenv("AUDIO_INPUT_DEVICE_NAME")
        if _name:
            self.input_device_name = _name.strip()
        _idx = os.getenv("AUDIO_INPUT_DEVICE_INDEX")
        if _idx is not None:
            try:
                self.input_device_index = int(_idx)
            except ValueError:
                pass


@dataclass
class VADConfig:
    sensitivity_preset: int = 2
    volume_threshold: float = 35.0
    confidence_threshold: float = 0.25
    detection_frames: int = 3
    confirmation_frames: int = 4
    silence_frames_limit: int = 14
    min_speech_duration: float = 0.8
    max_speech_duration: float = 20.0
    max_silence_duration: float = 1.2
    enable_noise_adaptation: bool = True
    noise_adaptation_frames: int = 24
    noise_multiplier: float = 2.6
    enable_debug: bool = False

    def apply_preset(self, preset: int) -> None:
        presets = {
            1: {
                "volume_threshold": 22.0,
                "confidence_threshold": 0.18,
                "detection_frames": 2,
                "confirmation_frames": 3,
                "silence_frames_limit": 12,
                "min_speech_duration": 0.6,
            },
            2: {
                "volume_threshold": 35.0,
                "confidence_threshold": 0.25,
                "detection_frames": 3,
                "confirmation_frames": 4,
                "silence_frames_limit": 14,
                "min_speech_duration": 0.8,
            },
            3: {
                "volume_threshold": 48.0,
                "confidence_threshold": 0.32,
                "detection_frames": 4,
                "confirmation_frames": 5,
                "silence_frames_limit": 16,
                "min_speech_duration": 1.0,
            },
        }
        values = presets.get(preset)
        if not values:
            return
        for key, value in values.items():
            setattr(self, key, value)
        self.sensitivity_preset = preset


@dataclass
class MusicAnalysisConfig:
    enabled: bool = True
    sample_rate: int = 16000
    chunk_size: int = 1024
    analysis_window: float = 1.2
    prewarm_timeout_seconds: float = 6.0
    feature_watchdog_seconds: float = 3.0
    tempo_fast_threshold: int = 140
    tempo_slow_threshold: int = 80
    energy_high_threshold: float = 0.5
    energy_low_threshold: float = 0.2
    enable_debug: bool = False


@dataclass
class AudioConfig:
    recording: AudioRecordingConfig = None
    vad: VADConfig = None
    music_analysis: MusicAnalysisConfig = None

    def __post_init__(self) -> None:
        self.recording = AudioRecordingConfig()
        self.vad = VADConfig()
        self.music_analysis = MusicAnalysisConfig()
        self.vad.apply_preset(self.vad.sensitivity_preset)


audio_config = AudioConfig()
