"""
核心模块

提供节拍跟踪、音乐分析、编舞算法等核心功能。
"""

from .beat_tracker import BeatTracker, BeatInfo
from .music_analyzer import MusicAnalyzer, MusicFeatures
from .choreographer import Choreographer, ChoreographyPlan

__all__ = [
    "BeatTracker",
    "BeatInfo",
    "MusicAnalyzer", 
    "MusicFeatures",
    "Choreographer",
    "ChoreographyPlan",
]
