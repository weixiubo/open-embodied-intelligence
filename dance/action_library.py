"""
舞蹈动作库管理器

负责加载、管理和查询舞蹈动作。
"""

import csv
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

from config import settings
from utils.logger import logger


@dataclass
class DanceAction:
    """
    舞蹈动作数据类
    
    Attributes:
        seq: 舵机控制板中的动作编号
        title: 动作名称
        label: 语音识别标签
        time_ms: 动作执行时长（毫秒）
        beats: 动作占用的节拍数
        type: 动作类型 (stand/forward/turn/side/gesture/combo)
        energy: 能量等级 (low/medium/high)
        tempo_match: 适合的节奏 (slow/medium/fast/any)
    """
    seq: str
    title: str
    label: str
    time_ms: int
    beats: int = 1
    type: str = "general"
    energy: str = "medium"
    tempo_match: str = "any"
    
    def __str__(self) -> str:
        return f"{self.label} ({self.time_ms/1000:.1f}s, {self.beats}拍, {self.type})"
    
    @property
    def duration_seconds(self) -> float:
        """动作时长（秒）"""
        return self.time_ms / 1000.0


class ActionLibrary:
    """
    舞蹈动作库管理器
    
    功能：
    - 从 CSV 文件加载动作
    - 按条件筛选动作
    - 获取动作数据
    """
    
    def __init__(self, csv_file: str = None):
        """
        初始化动作库
        
        Args:
            csv_file: CSV 动作文件路径（相对于项目根目录）
        """
        if csv_file is None:
            csv_file = "data/actions.csv"
        
        self.csv_path = settings.project_root / csv_file
        self.actions: List[DanceAction] = []
        self.action_map: Dict[str, DanceAction] = {}
        
        self._load_actions()
        logger.info(f"动作库加载完成: {len(self.actions)}个动作")
    
    def _load_actions(self) -> None:
        """从 CSV 文件加载动作"""
        if not self.csv_path.exists():
            logger.warning(f"动作库文件不存在: {self.csv_path}")
            return
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    action = DanceAction(
                        seq=row.get('seq', '000').strip(),
                        title=row.get('title', '').strip(),
                        label=row.get('label', '').strip(),
                        time_ms=int(row.get('time_ms', 1000)),
                        beats=int(row.get('beats', 1)),
                        type=row.get('type', 'general').strip(),
                        energy=row.get('energy', 'medium').strip(),
                        tempo_match=row.get('tempo_match', 'any').strip(),
                    )
                    
                    self.actions.append(action)
                    self.action_map[action.label] = action
                    
                    logger.debug(f"  加载动作: {action}")
                    
        except Exception as e:
            logger.error(f"加载动作库失败: {e}")
            raise
    
    def get_all_actions(self) -> List[DanceAction]:
        """获取所有动作"""
        return self.actions.copy()
    
    def get_action(self, label: str) -> Optional[DanceAction]:
        """根据标签获取动作"""
        return self.action_map.get(label)
    
    def get_action_data(self, label: str) -> Optional[dict]:
        """获取动作数据字典（兼容旧接口）"""
        action = self.get_action(label)
        if action:
            return {
                'seq': action.seq,
                'title': action.title,
                'time': action.time_ms,
                'beats': action.beats,
                'type': action.type,
            }
        return None
    
    def filter_by_time(self, max_time_ms: float) -> List[DanceAction]:
        """筛选时间内可完成的动作"""
        return [a for a in self.actions if a.time_ms <= max_time_ms]
    
    def filter_by_type(self, action_type: str) -> List[DanceAction]:
        """按类型筛选动作"""
        return [a for a in self.actions if a.type == action_type]
    
    def filter_by_energy(self, energy: str) -> List[DanceAction]:
        """按能量等级筛选动作"""
        return [a for a in self.actions if a.energy == energy]
    
    def filter_by_tempo(self, tempo_match: str) -> List[DanceAction]:
        """按节奏匹配筛选动作"""
        return [
            a for a in self.actions 
            if a.tempo_match == tempo_match or a.tempo_match == "any"
        ]
    
    def get_labels(self) -> List[str]:
        """获取所有动作标签"""
        return [a.label for a in self.actions]
    
    def get_shortest_action(self) -> Optional[DanceAction]:
        """获取最短的动作"""
        if not self.actions:
            return None
        return min(self.actions, key=lambda a: a.time_ms)
    
    def get_longest_action(self) -> Optional[DanceAction]:
        """获取最长的动作"""
        if not self.actions:
            return None
        return max(self.actions, key=lambda a: a.time_ms)
    
    def print_library(self) -> None:
        """打印动作库信息"""
        print(f"\n📚 动作库 ({len(self.actions)}个动作):")
        for action in self.actions:
            print(f"  {action.seq}: {action.label} - {action.title}")
            print(f"       时长: {action.time_ms/1000:.1f}s, 节拍: {action.beats}")
            print(f"       类型: {action.type}, 能量: {action.energy}, 节奏: {action.tempo_match}")
    
    def __len__(self) -> int:
        return len(self.actions)
    
    def __iter__(self):
        return iter(self.actions)
