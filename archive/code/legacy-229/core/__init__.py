"""
核心模块

包含音乐分析、节拍跟踪、编舞器等核心组件。
"""

from .music_analyzer import MusicAnalyzer, MusicFeatures
from .beat_tracker import BeatTracker
from .choreographer import Choreographer

__all__ = [
    'MusicAnalyzer',
    'MusicFeatures',
    'BeatTracker',
    'Choreographer',
]
