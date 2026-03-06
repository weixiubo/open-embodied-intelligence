"""
节拍跟踪器

提供实时节拍检测、预测和同步功能。
"""

import time
from dataclasses import dataclass, field
from typing import List, Optional
from collections import deque

from utils.logger import logger


@dataclass
class BeatInfo:
    """节拍信息"""
    time: float              # 节拍时间点（秒，相对于开始时间）
    absolute_time: float     # 绝对时间戳
    strength: float = 0.5    # 节拍强度 0-1
    beat_number: int = 0     # 节拍序号
    
    def __str__(self) -> str:
        return f"Beat#{self.beat_number} @ {self.time:.3f}s (strength={self.strength:.2f})"


@dataclass
class BeatTracker:
    """
    实时节拍跟踪器
    
    功能：
    - 维护检测到的节拍队列
    - 预测下一个节拍时间
    - 判断当前是否在节拍点上
    """
    
    # 节拍缓冲区
    beat_buffer: deque = field(default_factory=lambda: deque(maxlen=32))
    
    # 当前状态
    current_tempo: float = 120.0      # 当前 BPM
    beat_interval: float = 0.5        # 节拍间隔（秒）
    last_beat_time: float = 0.0       # 上一个节拍时间
    beat_count: int = 0               # 总节拍计数
    
    # 起始时间
    start_time: float = field(default_factory=time.time)
    
    # 配置
    min_tempo: float = 60.0           # 最小 BPM
    max_tempo: float = 200.0          # 最大 BPM
    
    def reset(self) -> None:
        """重置跟踪器状态"""
        self.beat_buffer.clear()
        self.current_tempo = 120.0
        self.beat_interval = 0.5
        self.last_beat_time = 0.0
        self.beat_count = 0
        self.start_time = time.time()
        logger.debug("节拍跟踪器已重置")
    
    def update_tempo(self, tempo: float) -> None:
        """
        更新当前 BPM
        
        Args:
            tempo: 检测到的 BPM
        """
        # 限制在合理范围内
        tempo = max(self.min_tempo, min(self.max_tempo, tempo))
        
        # 平滑更新（避免突变）
        self.current_tempo = 0.7 * self.current_tempo + 0.3 * tempo
        self.beat_interval = 60.0 / self.current_tempo
        
        logger.debug(f"BPM 更新: {self.current_tempo:.1f} (间隔: {self.beat_interval:.3f}s)")
    
    def add_beats(self, beat_times: List[float], strengths: Optional[List[float]] = None) -> None:
        """
        添加检测到的节拍
        
        Args:
            beat_times: 节拍时间点列表（相对时间，秒）
            strengths: 节拍强度列表（可选）
        """
        current_time = time.time()
        
        if strengths is None:
            strengths = [0.5] * len(beat_times)
        
        for t, s in zip(beat_times, strengths):
            beat = BeatInfo(
                time=t,
                absolute_time=self.start_time + t,
                strength=s,
                beat_number=self.beat_count
            )
            self.beat_buffer.append(beat)
            self.beat_count += 1
            
            # 更新最后节拍时间
            if t > self.last_beat_time:
                self.last_beat_time = t
        
        logger.debug(f"添加 {len(beat_times)} 个节拍，总计 {self.beat_count} 个")
    
    def get_next_beat_time(self) -> float:
        """
        预测下一个节拍的时间点
        
        Returns:
            下一个节拍的绝对时间戳
        """
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        if self.last_beat_time > 0:
            # 基于上一个节拍预测
            beats_since_last = int((elapsed - self.last_beat_time) / self.beat_interval)
            next_beat = self.last_beat_time + (beats_since_last + 1) * self.beat_interval
        else:
            # 没有历史数据，基于开始时间预测
            beats_since_start = int(elapsed / self.beat_interval)
            next_beat = (beats_since_start + 1) * self.beat_interval
        
        return self.start_time + next_beat
    
    def time_to_next_beat(self) -> float:
        """
        获取距离下一个节拍的时间
        
        Returns:
            距离下一个节拍的时间（毫秒）
        """
        next_beat_time = self.get_next_beat_time()
        time_remaining = next_beat_time - time.time()
        return max(0, time_remaining * 1000)  # 转换为毫秒
    
    def is_on_beat(self, tolerance_ms: float = 50.0) -> bool:
        """
        判断当前是否在节拍点上
        
        Args:
            tolerance_ms: 容差（毫秒）
        
        Returns:
            是否在节拍点上
        """
        time_to_beat = self.time_to_next_beat()
        time_since_beat = (self.beat_interval * 1000) - time_to_beat
        
        # 检查是否接近上一个或下一个节拍
        return min(time_to_beat, time_since_beat) <= tolerance_ms
    
    def wait_for_beat(self, timeout: float = 2.0) -> bool:
        """
        等待下一个节拍
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            是否成功等到节拍
        """
        start_wait = time.time()
        
        while True:
            if self.is_on_beat():
                return True
            
            if time.time() - start_wait > timeout:
                logger.warning(f"等待节拍超时 ({timeout}s)")
                return False
            
            # 短暂休眠
            time.sleep(0.01)  # 10ms
    
    def get_beat_phase(self) -> float:
        """
        获取当前在节拍周期中的相位
        
        Returns:
            相位值 0.0-1.0（0.0 = 刚好在节拍上，0.5 = 节拍中间）
        """
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        # 计算在当前节拍周期中的位置
        phase = (elapsed % self.beat_interval) / self.beat_interval
        return phase
    
    def get_beats_per_measure(self, measure_beats: int = 4) -> int:
        """
        获取当前在小节中的第几拍
        
        Args:
            measure_beats: 每小节拍数（默认 4/4 拍）
        
        Returns:
            当前拍号（1 到 measure_beats）
        """
        return (self.beat_count % measure_beats) + 1
    
    @property
    def tempo(self) -> float:
        """当前 BPM"""
        return self.current_tempo
    
    @property
    def interval_ms(self) -> float:
        """节拍间隔（毫秒）"""
        return self.beat_interval * 1000
    
    def get_status(self) -> dict:
        """获取跟踪器状态"""
        return {
            "tempo": self.current_tempo,
            "beat_interval_ms": self.interval_ms,
            "beat_count": self.beat_count,
            "buffer_size": len(self.beat_buffer),
            "elapsed_time": time.time() - self.start_time,
            "phase": self.get_beat_phase(),
        }
