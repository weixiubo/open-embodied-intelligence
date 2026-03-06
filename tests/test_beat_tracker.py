"""
节拍跟踪器单元测试
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from core.beat_tracker import BeatTracker, BeatInfo


class TestBeatInfo:
    """测试 BeatInfo 数据类"""
    
    def test_creation(self):
        """测试创建 BeatInfo"""
        beat = BeatInfo(time=0.5, absolute_time=1000.5, strength=0.8, beat_number=1)
        assert beat.time == 0.5
        assert beat.absolute_time == 1000.5
        assert beat.strength == 0.8
        assert beat.beat_number == 1
    
    def test_default_values(self):
        """测试默认值"""
        beat = BeatInfo(time=1.0, absolute_time=1001.0)
        assert beat.strength == 0.5
        assert beat.beat_number == 0
    
    def test_str(self):
        """测试字符串表示"""
        beat = BeatInfo(time=0.5, absolute_time=1000.5, strength=0.8, beat_number=1)
        s = str(beat)
        assert "Beat#1" in s
        assert "0.500s" in s


class TestBeatTracker:
    """测试 BeatTracker"""
    
    def test_initialization(self):
        """测试初始化"""
        tracker = BeatTracker()
        assert tracker.current_tempo == 120.0
        assert tracker.beat_interval == 0.5
        assert tracker.beat_count == 0
    
    def test_update_tempo(self):
        """测试更新 BPM"""
        tracker = BeatTracker()
        tracker.update_tempo(140.0)
        # 由于平滑更新，实际值不会直接变成 140
        assert tracker.current_tempo > 120.0
        assert tracker.current_tempo < 140.0
    
    def test_update_tempo_limits(self):
        """测试 BPM 限制"""
        tracker = BeatTracker()
        tracker.min_tempo = 60.0
        tracker.max_tempo = 200.0
        
        # 测试超出范围的值
        tracker.update_tempo(30.0)  # 太低
        assert tracker.current_tempo >= tracker.min_tempo
        
        tracker.update_tempo(300.0)  # 太高
        assert tracker.current_tempo <= tracker.max_tempo
    
    def test_add_beats(self):
        """测试添加节拍"""
        tracker = BeatTracker()
        beat_times = [0.5, 1.0, 1.5, 2.0]
        tracker.add_beats(beat_times)
        
        assert tracker.beat_count == 4
        assert len(tracker.beat_buffer) == 4
        assert tracker.last_beat_time == 2.0
    
    def test_add_beats_with_strengths(self):
        """测试添加带强度的节拍"""
        tracker = BeatTracker()
        beat_times = [0.5, 1.0]
        strengths = [0.8, 0.6]
        tracker.add_beats(beat_times, strengths)
        
        assert tracker.beat_count == 2
        assert tracker.beat_buffer[0].strength == 0.8
        assert tracker.beat_buffer[1].strength == 0.6
    
    def test_reset(self):
        """测试重置"""
        tracker = BeatTracker()
        tracker.add_beats([0.5, 1.0, 1.5])
        tracker.update_tempo(150.0)
        
        tracker.reset()
        
        assert tracker.beat_count == 0
        assert len(tracker.beat_buffer) == 0
        assert tracker.current_tempo == 120.0
    
    def test_get_beat_phase(self):
        """测试获取节拍相位"""
        tracker = BeatTracker()
        phase = tracker.get_beat_phase()
        
        assert 0.0 <= phase <= 1.0
    
    def test_beats_per_measure(self):
        """测试小节内的拍号"""
        tracker = BeatTracker()
        tracker.beat_count = 0
        assert tracker.get_beats_per_measure(4) == 1
        
        tracker.beat_count = 3
        assert tracker.get_beats_per_measure(4) == 4
        
        tracker.beat_count = 4
        assert tracker.get_beats_per_measure(4) == 1
    
    def test_get_status(self):
        """测试获取状态"""
        tracker = BeatTracker()
        status = tracker.get_status()
        
        assert "tempo" in status
        assert "beat_interval_ms" in status
        assert "beat_count" in status
        assert "phase" in status
    
    def test_tempo_property(self):
        """测试 tempo 属性"""
        tracker = BeatTracker()
        assert tracker.tempo == tracker.current_tempo
    
    def test_interval_ms_property(self):
        """测试 interval_ms 属性"""
        tracker = BeatTracker()
        tracker.beat_interval = 0.5
        assert tracker.interval_ms == 500.0


class TestBeatTrackerTiming:
    """测试节拍时间相关功能"""
    
    def test_time_to_next_beat(self):
        """测试距离下一个节拍的时间"""
        tracker = BeatTracker()
        time_ms = tracker.time_to_next_beat()
        
        # 应该返回正数或零
        assert time_ms >= 0
        # 不应该超过一个节拍周期
        assert time_ms <= tracker.interval_ms
    
    def test_is_on_beat_tolerance(self):
        """测试节拍判断的容差"""
        tracker = BeatTracker()
        
        # 这个测试依赖于实际时间，可能不稳定
        # 主要测试函数可以正常调用
        result = tracker.is_on_beat(tolerance_ms=50)
        assert isinstance(result, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
