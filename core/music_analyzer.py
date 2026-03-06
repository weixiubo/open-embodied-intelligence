"""
音乐分析器

使用 librosa 进行实时音乐特征提取和节拍检测。
"""

import time
import threading
import queue
from dataclasses import dataclass, field
from typing import Optional, Callable, List

import numpy as np

from config import audio_config
from utils.logger import logger

# 尝试导入 librosa
try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False
    logger.warning("librosa 未安装，音乐分析功能将被禁用")

# 尝试导入 pyaudio
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    logger.warning("pyaudio 未安装，无法进行实时音频采集")


@dataclass
class MusicFeatures:
    """音乐特征数据类"""
    
    # 基础特征
    tempo: float = 120.0                # BPM
    beat_times: List[float] = field(default_factory=list)  # 精确节拍时间点
    beat_strength: float = 0.5          # 节拍强度
    energy: float = 0.0                 # 音频能量
    
    # 频谱特征
    spectral_centroid: float = 0.0      # 频谱重心
    zero_crossing_rate: float = 0.0     # 过零率
    onset_strength: float = 0.0         # 起始强度
    
    # 分类特征
    rhythm_pattern: str = "steady"      # 节奏模式: fast/slow/steady/strong/gentle
    mood: str = "neutral"               # 情绪: energetic/calm/bright/dark/neutral
    
    # 音乐结构
    segment_type: str = "unknown"       # 段落类型: intro/verse/chorus/bridge/outro
    segment_intensity: float = 0.5      # 段落强度
    energy_trend: str = "stable"        # 能量趋势: rising/falling/stable
    
    # 元数据
    timestamp: float = 0.0              # 时间戳
    confidence: float = 0.5             # 分析置信度
    
    def get_beat_interval_ms(self) -> float:
        """获取节拍间隔（毫秒）"""
        if self.tempo > 0:
            return 60000.0 / self.tempo
        return 500.0  # 默认 120 BPM


class MusicAnalyzer:
    """
    实时音乐分析器
    
    功能：
    - 实时采集音频
    - 提取音乐特征（BPM、节拍、能量等）
    - 检测精确的节拍时间点
    """
    
    def __init__(
        self,
        sample_rate: int = None,
        chunk_size: int = None,
        analysis_window: float = None,
        enabled: bool = True,
    ):
        """
        初始化音乐分析器
        
        Args:
            sample_rate: 音频采样率
            chunk_size: 音频块大小
            analysis_window: 分析窗口时长（秒）
            enabled: 是否启用分析功能
        """
        config = audio_config.music_analysis
        
        self.sample_rate = sample_rate or config.sample_rate
        self.chunk_size = chunk_size or config.chunk_size
        self.analysis_window = analysis_window or config.analysis_window
        self.enabled = enabled and LIBROSA_AVAILABLE
        
        # 音频缓冲区
        self.audio_buffer: queue.Queue = queue.Queue(maxsize=100)
        self.analysis_buffer: List[float] = []
        self.buffer_duration: float = 0.0
        
        # 分析结果
        self.current_features = MusicFeatures()
        self.features_history: List[MusicFeatures] = []
        self.max_history = 10
        
        # 线程控制
        self.is_analyzing = False
        self.analysis_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # 回调函数
        self.feature_callback: Optional[Callable[[MusicFeatures], None]] = None
        
        # 音频设备
        self.audio = None
        self.stream = None

        # 降低环境噪音误触发，同时缩短首次有效输入等待。
        self.noise_threshold = 250
        self.valid_signal_count = 0
        self.required_valid_frames = 2
        
        if not self.enabled:
            logger.warning("音乐分析功能已禁用")
        else:
            logger.info("音乐分析器初始化完成")
    
    def set_feature_callback(self, callback: Callable[[MusicFeatures], None]) -> None:
        """设置特征更新回调函数"""
        self.feature_callback = callback
    
    def start(self) -> bool:
        """开始音乐分析"""
        if not self.enabled:
            logger.warning("音乐分析功能未启用")
            return False
        
        if self.is_analyzing:
            logger.warning("音乐分析已在运行")
            return False
        
        if not PYAUDIO_AVAILABLE:
            logger.error("pyaudio 不可用，无法进行音乐分析")
            return False
        
        try:
            # 初始化音频设备
            self.audio = pyaudio.PyAudio()
            
            # 创建音频流
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback,
            )
            
            # 启动分析线程
            self.is_analyzing = True
            self.stop_event.clear()
            self.analysis_thread = threading.Thread(
                target=self._analysis_loop,
                daemon=True,
            )
            self.analysis_thread.start()
            
            # 开始音频流
            self.stream.start_stream()
            
            logger.info("音乐分析已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动音乐分析失败: {e}")
            self.stop()
            return False
    
    def stop(self) -> None:
        """停止音乐分析"""
        if not self.is_analyzing:
            return
        
        logger.info("停止音乐分析")
        
        # 停止线程
        self.is_analyzing = False
        self.stop_event.set()
        
        # 停止音频流
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        
        if self.audio:
            try:
                self.audio.terminate()
            except Exception:
                pass
            self.audio = None
        
        # 等待线程结束
        if self.analysis_thread and self.analysis_thread.is_alive():
            self.analysis_thread.join(timeout=2)
        
        # 清理缓冲区
        while not self.audio_buffer.empty():
            try:
                self.audio_buffer.get_nowait()
            except Exception:
                break
        
        self.analysis_buffer.clear()
        self.buffer_duration = 0.0
        self.valid_signal_count = 0
        logger.info("音乐分析已停止")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频回调函数"""
        _ = frame_count, time_info, status  # 忽略未使用的参数
        if self.is_analyzing:
            try:
                audio_data = np.frombuffer(in_data, dtype=np.float32)
                rms = float(np.sqrt(np.mean(audio_data ** 2)) * 32768)

                if rms > self.noise_threshold:
                    self.valid_signal_count += 1
                    if (
                        self.valid_signal_count >= self.required_valid_frames
                        and not self.audio_buffer.full()
                    ):
                        self.audio_buffer.put(audio_data)
                else:
                    self.valid_signal_count = 0
            except Exception:
                pass
        
        return (None, pyaudio.paContinue) if PYAUDIO_AVAILABLE else (None, 0)
    
    def _analysis_loop(self) -> None:
        """音乐分析主循环"""
        logger.debug("音乐分析循环启动")
        
        while self.is_analyzing and not self.stop_event.is_set():
            try:
                if not self.audio_buffer.empty():
                    audio_chunk = self.audio_buffer.get(timeout=0.1)
                    self._process_audio_chunk(audio_chunk)
                else:
                    time.sleep(0.05)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning(f"音乐分析错误: {e}")
                time.sleep(0.1)
        
        logger.debug("音乐分析循环结束")
    
    def _process_audio_chunk(self, audio_chunk: np.ndarray) -> None:
        """处理音频块"""
        # 添加到分析缓冲区
        self.analysis_buffer.extend(audio_chunk.tolist())
        self.buffer_duration += len(audio_chunk) / self.sample_rate
        
        # 当缓冲区达到分析窗口大小时进行分析
        if self.buffer_duration >= self.analysis_window:
            self._analyze_buffer()
            
            # 保留一半数据作为重叠窗口
            overlap_samples = len(self.analysis_buffer) // 2
            self.analysis_buffer = self.analysis_buffer[-overlap_samples:]
            self.buffer_duration = len(self.analysis_buffer) / self.sample_rate
    
    def _analyze_buffer(self) -> None:
        """分析音频缓冲区"""
        if len(self.analysis_buffer) < self.sample_rate * 0.5:
            return
        
        try:
            audio_data = np.array(self.analysis_buffer, dtype=np.float32)
            features = self._extract_features(audio_data)
            
            # 更新当前特征
            self.current_features = features
            
            # 添加到历史记录
            self.features_history.append(features)
            if len(self.features_history) > self.max_history:
                self.features_history.pop(0)
            
            # 调用回调函数
            if self.feature_callback:
                try:
                    self.feature_callback(features)
                except Exception as e:
                    logger.warning(f"特征回调函数错误: {e}")
                    
        except Exception as e:
            logger.warning(f"音频分析错误: {e}")
    
    def _extract_features(self, audio_data: np.ndarray) -> MusicFeatures:
        """提取音乐特征"""
        features = MusicFeatures()
        features.timestamp = time.time()
        
        try:
            # 基础特征
            features.energy = float(np.mean(audio_data ** 2))
            features.zero_crossing_rate = float(
                np.mean(librosa.feature.zero_crossing_rate(audio_data)[0])
            )
            
            if len(audio_data) > 512:
                # 频谱特征
                spectral_centroids = librosa.feature.spectral_centroid(
                    y=audio_data, sr=self.sample_rate
                )[0]
                features.spectral_centroid = float(np.mean(spectral_centroids))
                
                # 节拍检测（核心功能）
                try:
                    hop_length = 512
                    tempo, beat_frames = librosa.beat.beat_track(
                        y=audio_data, sr=self.sample_rate, hop_length=hop_length
                    )
                    features.tempo = float(tempo)
                    
                    # 【关键】提取精确的节拍时间点
                    features.beat_times = librosa.frames_to_time(
                        beat_frames, sr=self.sample_rate, hop_length=hop_length
                    ).tolist()
                    
                    # 起始强度
                    onset_envelope = librosa.onset.onset_strength(
                        y=audio_data, sr=self.sample_rate
                    )
                    features.onset_strength = float(np.mean(onset_envelope))
                    features.beat_strength = float(np.std(onset_envelope))
                    
                except Exception:
                    features.tempo = 120.0
                    features.beat_times = []
                    features.beat_strength = 0.5
                    features.onset_strength = 0.5
            
            # 分析节奏模式和情绪
            features.rhythm_pattern = self._analyze_rhythm_pattern(features)
            features.mood = self._analyze_mood(features)
            features.confidence = 0.8
            
        except Exception as e:
            logger.warning(f"特征提取错误: {e}")
            features.tempo = 120.0
            features.energy = 0.1
            features.rhythm_pattern = "steady"
            features.mood = "neutral"
            features.confidence = 0.3
        
        return features
    
    def _analyze_rhythm_pattern(self, features: MusicFeatures) -> str:
        """分析节奏模式"""
        config = audio_config.music_analysis
        
        if features.tempo > config.tempo_fast_threshold:
            return "fast"
        elif features.tempo < config.tempo_slow_threshold:
            return "slow"
        elif features.beat_strength > 0.7:
            return "strong"
        elif features.beat_strength < 0.3:
            return "gentle"
        else:
            return "steady"
    
    def _analyze_mood(self, features: MusicFeatures) -> str:
        """分析音乐情绪"""
        config = audio_config.music_analysis
        
        if features.energy > config.energy_high_threshold and features.tempo > 120:
            return "energetic"
        elif features.energy < config.energy_low_threshold and features.tempo < 90:
            return "calm"
        elif features.spectral_centroid > 2000:
            return "bright"
        elif features.spectral_centroid < 1000:
            return "dark"
        else:
            return "neutral"
    
    def get_current_features(self) -> MusicFeatures:
        """获取当前音乐特征"""
        return self.current_features

    def has_recent_features(self, max_age_seconds: float = None) -> bool:
        """最近是否收到过有效特征。"""
        max_age_seconds = (
            max_age_seconds
            or audio_config.music_analysis.feature_watchdog_seconds
        )
        if not self.current_features.timestamp:
            return False
        return (time.time() - self.current_features.timestamp) <= max_age_seconds
    
    def get_beat_times(self) -> List[float]:
        """获取当前检测到的节拍时间点"""
        return self.current_features.beat_times
    
    @property
    def is_active(self) -> bool:
        """是否正在分析"""
        return self.is_analyzing
