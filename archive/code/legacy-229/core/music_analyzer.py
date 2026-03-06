"""
音乐分析器

使用 librosa 进行实时音乐特征提取和节拍检测。
【增强版】增加详细的阶段性调试输出。
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
        
        # 调试统计
        self.analysis_count = 0
        self.callback_count = 0
        
        # 【问题3】音频质量监控
        self.noise_threshold = 400  # 噪声阈值（提升至400）
        self.valid_signal_count = 0  # 连续有效信号帧数
        self.required_valid_frames = 3  # 需要连续3帧有效信号才触发
        
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
        
        logger.debug("【音乐分析】进入: start()")
        
        try:
            # 初始化音频设备
            self.audio = pyaudio.PyAudio()
            logger.debug(f"【音乐分析】PyAudio初始化成功")
            
            # 创建音频流
            logger.debug(f"【音乐分析】开始创建音频流: sample_rate={self.sample_rate}, chunk_size={self.chunk_size}")
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback,
            )
            logger.debug(f"【音乐分析】音频流创建成功")
            
            # 启动分析线程
            self.is_analyzing = True
            self.stop_event.clear()
            self.analysis_thread = threading.Thread(
                target=self._analysis_loop,
                daemon=True,
            )
            self.analysis_thread.start()
            logger.debug(f"【音乐分析】分析线程已启动")
            
            # 开始音频流
            self.stream.start_stream()
            logger.debug(f"【音乐分析】音频流已启动")
            
            logger.info("音乐分析已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动音乐分析失败: {e}")
            logger.debug(f"【音乐分析】异常退出: start() - {e}")
            self.stop()
            return False
    
    def stop(self) -> None:
        """停止音乐分析"""
        if not self.is_analyzing:
            return
        
        logger.debug("【音乐分析】进入: stop()")
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
        logger.debug(f"【音乐分析】退出: stop() - 总分析次数={self.analysis_count}, 回调次数={self.callback_count}")
        logger.info("音乐分析已停止")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音频回调函数"""
        _ = frame_count, time_info, status  # 忽略未使用的参数
        if self.is_analyzing:
            try:
                audio_data = np.frombuffer(in_data, dtype=np.float32)
                
                # 【问题3】计算实时音量（RMS）
                rms = np.sqrt(np.mean(audio_data ** 2)) * 32768  # 转换为int16范围
                
                # 【问题3】噪声过滤判定
                if rms > self.noise_threshold:
                    self.valid_signal_count += 1
                    logger.debug(f"【音频采集】有效信号 RMS={rms:.1f} > {self.noise_threshold} (连续{self.valid_signal_count}帧)")
                    
                    if self.valid_signal_count >= self.required_valid_frames:
                        if not self.audio_buffer.full():
                            self.audio_buffer.put(audio_data)
                else:
                    if self.valid_signal_count > 0:
                        logger.debug(f"【音频采集】噪声过滤 RMS={rms:.1f} < {self.noise_threshold} (重置计数)")
                    self.valid_signal_count = 0
            except Exception:
                pass
        
        return (None, pyaudio.paContinue) if PYAUDIO_AVAILABLE else (None, 0)
    
    def _analysis_loop(self) -> None:
        """音乐分析主循环"""
        logger.debug("【音乐分析循环】进入: _analysis_loop()")
        
        while self.is_analyzing and not self.stop_event.is_set():
            try:
                if not self.audio_buffer.empty():
                    audio_chunk = self.audio_buffer.get(timeout=0.1)
                    logger.debug(f"【音乐分析循环】收到音频块: {len(audio_chunk)}样本")
                    self._process_audio_chunk(audio_chunk)
                else:
                    time.sleep(0.05)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.warning(f"音乐分析错误: {e}")
                time.sleep(0.1)
        
        logger.debug("【音乐分析循环】退出: _analysis_loop()")
    
    def _process_audio_chunk(self, audio_chunk: np.ndarray) -> None:
        """处理音频块"""
        # 添加到分析缓冲区
        self.analysis_buffer.extend(audio_chunk.tolist())
        self.buffer_duration += len(audio_chunk) / self.sample_rate
        
        logger.debug(f"【音频块处理】缓冲区时长: {self.buffer_duration:.2f}s/{self.analysis_window:.2f}s, 样本数: {len(self.analysis_buffer)}")
        
        # 当缓冲区达到分析窗口大小时进行分析
        if self.buffer_duration >= self.analysis_window:
            logger.debug(f"【音频块处理】缓冲区已就绪，进行分析...")
            self._analyze_buffer()
            
            # 保留一半数据作为重叠窗口
            overlap_samples = len(self.analysis_buffer) // 2
            self.analysis_buffer = self.analysis_buffer[-overlap_samples:]
            self.buffer_duration = len(self.analysis_buffer) / self.sample_rate
            logger.debug(f"【音频块处理】缓冲区重置: 保留{overlap_samples}样本")
    
    def _analyze_buffer(self) -> None:
        """分析音频缓冲区"""
        if len(self.analysis_buffer) < self.sample_rate * 0.5:
            logger.debug(f"【缓冲区分析】缓冲区过短({len(self.analysis_buffer)}样本), 跳过分析")
            return
        
        logger.debug(f"【缓冲区分析】进入: _analyze_buffer() - 缓冲区大小: {len(self.analysis_buffer)}")
        
        try:
            audio_data = np.array(self.analysis_buffer, dtype=np.float32)
            features = self._extract_features(audio_data)
            
            self.analysis_count += 1
            
            logger.debug(
                f"【缓冲区分析】特征提取完成 (#{self.analysis_count}): "
                f"energy={features.energy:.6f}, "
                f"tempo={features.tempo:.1f}, "
                f"beat_count={len(features.beat_times)}, "
                f"onset_strength={features.onset_strength:.6f}, "
                f"mood={features.mood}"
            )
            
            # 更新当前特征
            self.current_features = features
            
            # 添加到历史记录
            self.features_history.append(features)
            if len(self.features_history) > self.max_history:
                self.features_history.pop(0)
            
            # 调用回调函数
            if self.feature_callback:
                try:
                    self.callback_count += 1
                    logger.debug(f"【缓冲区分析】执行回调函数 (#{self.callback_count})")
                    self.feature_callback(features)
                except Exception as e:
                    logger.warning(f"特征回调函数错误: {e}")
                    
        except Exception as e:
            logger.warning(f"音频分析错误: {e}")
            logger.debug(f"【缓冲区分析】异常: {e}")
    
    def _extract_features(self, audio_data: np.ndarray) -> MusicFeatures:
        """提取音乐特征"""
        logger.debug(f"【特征提取】进入: 音频长度={len(audio_data)}")
        
        features = MusicFeatures()
        features.timestamp = time.time()
        
        try:
            # 基础特征
            features.energy = float(np.mean(audio_data ** 2))
            features.zero_crossing_rate = float(
                np.mean(librosa.feature.zero_crossing_rate(audio_data)[0])
            )
            logger.debug(f"【特征提取】基础特征: energy={features.energy:.6f}, zcr={features.zero_crossing_rate:.6f}")
            
            if len(audio_data) > 512:
                # 频谱特征
                spectral_centroids = librosa.feature.spectral_centroid(
                    y=audio_data, sr=self.sample_rate
                )[0]
                features.spectral_centroid = float(np.mean(spectral_centroids))
                logger.debug(f"【特征提取】频谱重心: {features.spectral_centroid:.2f}")
                
                # 节拍检测（核心功能）
                try:
                    logger.debug(f"【特征提取】开始节拍检测...")
                    tempo, beat_frames = librosa.beat.beat_track(
                        y=audio_data, sr=self.sample_rate
                    )
                    features.tempo = float(tempo)
                    
                    # 【关键】提取精确的节拍时间点
                    features.beat_times = librosa.frames_to_time(
                        beat_frames, sr=self.sample_rate
                    ).tolist()
                    
                    logger.debug(f"【特征提取】节拍检测完成: tempo={features.tempo:.1f}, beat_count={len(features.beat_times)}")
                    
                    # 起始强度
                    onset_envelope = librosa.onset.onset_strength(
                        y=audio_data, sr=self.sample_rate
                    )
                    features.onset_strength = float(np.mean(onset_envelope))
                    features.beat_strength = float(np.std(onset_envelope))
                    
                    logger.debug(f"【特征提取】起始强度: onset={features.onset_strength:.6f}, beat_strength={features.beat_strength:.6f}")
                    
                except Exception as e:
                    logger.debug(f"【特征提取】节拍检测失败: {e}, 使用默认值")
                    features.tempo = 120.0
                    features.beat_times = []
                    features.onset_strength = 0.0
                    features.beat_strength = 0.0

            features.rhythm_pattern = self._analyze_rhythm_pattern(features)
            features.mood = self._analyze_mood(features)
            features.confidence = 0.8

            logger.debug(f"【特征提取】情绪分析: rhythm={features.rhythm_pattern}, mood={features.mood}, tempo={features.tempo:.1f}BPM")
            
        except Exception as e:
            logger.warning(f"特征提取错误: {e}")
            logger.debug(f"【特征提取】异常退出: {e}")
            features.tempo = 120.0
            features.energy = 0.1
            features.rhythm_pattern = "steady"
            features.mood = "neutral"
            features.confidence = 0.3
        
        logger.debug(f"【特征提取】退出: 完整特征={features}")
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
    
    def get_beat_times(self) -> List[float]:
        """获取当前检测到的节拍时间点"""
        return self.current_features.beat_times
    
    @property
    def is_active(self) -> bool:
        """是否正在分析"""
        return self.is_analyzing
