"""
音频配置模块

音频录制、VAD、音乐分析相关的配置。
"""

from dataclasses import dataclass


@dataclass
class AudioRecordingConfig:
    """音频录制配置"""
    sample_rate: int = 16000  # 采样率（Hz），百度 API 兼容
    channels: int = 1         # 单声道
    chunk_size: int = 1024    # 音频块大小
    format_bits: int = 16     # 位深度
    max_recording_duration: float = 15.0  # 最大录音时长（秒）


@dataclass
class VADConfig:
    """语音活动检测配置"""
    # 敏感度预设 (1=高敏感, 2=中等, 3=低敏感, 4=超低)
    sensitivity_preset: int = 2
    
    # 阈值参数（会根据预设自动调整）
    volume_threshold: float = 35.0
    confidence_threshold: float = 0.25
    
    # 帧数参数
    detection_frames: int = 3
    confirmation_frames: int = 4
    silence_frames_limit: int = 15
    
    # 时长参数
    min_speech_duration: float = 1.0   # 最小语音时长（秒）
    max_speech_duration: float = 20.0  # 最大语音时长（秒）
    max_silence_duration: float = 1.2  # 最大静音时长（秒）
    
    # 自适应参数
    enable_noise_adaptation: bool = True
    noise_adaptation_frames: int = 30
    noise_multiplier: float = 3.5
    
    # 调试
    enable_debug: bool = False
    
    def apply_preset(self, preset: int) -> None:
        """应用预设配置"""
        presets = {
            1: {  # 高敏感度
                "volume_threshold": 25.0,
                "confidence_threshold": 0.15,
                "detection_frames": 2,
                "confirmation_frames": 3,
                "silence_frames_limit": 12,
                "min_speech_duration": 0.8,
            },
            2: {  # 中等敏感度
                "volume_threshold": 35.0,
                "confidence_threshold": 0.25,
                "detection_frames": 3,
                "confirmation_frames": 4,
                "silence_frames_limit": 15,
                "min_speech_duration": 1.0,
            },
            3: {  # 低敏感度
                "volume_threshold": 45.0,
                "confidence_threshold": 0.35,
                "detection_frames": 4,
                "confirmation_frames": 5,
                "silence_frames_limit": 18,
                "min_speech_duration": 1.2,
            },
            4: {  # 超低敏感度
                "volume_threshold": 60.0,
                "confidence_threshold": 0.45,
                "detection_frames": 5,
                "confirmation_frames": 6,
                "silence_frames_limit": 22,
                "min_speech_duration": 1.5,
            },
        }
        
        if preset in presets:
            for key, value in presets[preset].items():
                setattr(self, key, value)
            self.sensitivity_preset = preset


@dataclass
class MusicAnalysisConfig:
    """音乐分析配置"""
    enabled: bool = True
    sample_rate: int = 22050      # 音乐分析采样率
    chunk_size: int = 1024
    analysis_window: float = 1.2  # 【修改】分析窗口时长 2.0 → 1.2 秒
    
    # 节拍阈值
    tempo_fast_threshold: int = 140   # 快节奏阈值 (BPM)
    tempo_slow_threshold: int = 80    # 慢节奏阈值 (BPM)
    
    # 能量阈值
    energy_high_threshold: float = 0.5
    energy_low_threshold: float = 0.2
    
    # 调试
    enable_debug: bool = False


@dataclass
class AudioConfig:
    """音频配置汇总"""
    recording: AudioRecordingConfig = None
    vad: VADConfig = None
    music_analysis: MusicAnalysisConfig = None
    
    def __post_init__(self) -> None:
        self.recording = AudioRecordingConfig()
        self.vad = VADConfig()
        self.music_analysis = MusicAnalysisConfig()
        
        # 应用 VAD 预设
        self.vad.apply_preset(self.vad.sensitivity_preset)


# 全局音频配置实例
audio_config = AudioConfig()
