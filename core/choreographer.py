"""
智能编舞器

基于音乐特征和马尔可夫链的舞蹈动作编排系统。
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import numpy as np

from config import dance_config
from utils.logger import logger
from .beat_tracker import BeatTracker
from .music_analyzer import MusicFeatures


@dataclass
class ChoreographyPlan:
    """编舞计划"""
    actions: List[str] = field(default_factory=list)       # 动作序列
    beat_targets: List[int] = field(default_factory=list)  # 每个动作的目标节拍
    total_beats: int = 0                                   # 总节拍数
    total_duration_ms: int = 0                             # 总时长（毫秒）


class MarkovChain:
    """动作转移矩阵"""
    
    # 动作类型之间的转移概率
    TYPE_TRANSITIONS = {
        "stand":   {"forward": 0.30, "gesture": 0.20, "turn": 0.15, "side": 0.10, "dance": 0.15, "left": 0.05, "right": 0.05, "stand": 0.00},
        "forward": {"turn": 0.20, "side": 0.15, "stand": 0.15, "gesture": 0.10, "dance": 0.25, "left": 0.10, "right": 0.05, "forward": 0.00},
        "turn":    {"forward": 0.25, "side": 0.15, "stand": 0.15, "gesture": 0.10, "dance": 0.20, "left": 0.10, "right": 0.05, "turn": 0.00},
        "side":    {"forward": 0.20, "turn": 0.20, "stand": 0.15, "gesture": 0.10, "dance": 0.20, "left": 0.10, "right": 0.05, "side": 0.00},
        "gesture": {"forward": 0.20, "stand": 0.15, "turn": 0.15, "side": 0.10, "dance": 0.25, "left": 0.10, "right": 0.05, "gesture": 0.00},
        "combo":   {"stand": 0.25, "gesture": 0.20, "forward": 0.15, "turn": 0.10, "dance": 0.20, "left": 0.05, "right": 0.05, "side": 0.00},
        "dance":   {"dance": 0.35, "gesture": 0.20, "forward": 0.15, "stand": 0.10, "left": 0.10, "right": 0.05, "turn": 0.05, "side": 0.00},
        "left":    {"right": 0.35, "dance": 0.30, "forward": 0.15, "stand": 0.10, "gesture": 0.05, "turn": 0.05, "side": 0.00, "left": 0.00},
        "right":   {"left": 0.35, "dance": 0.30, "forward": 0.15, "stand": 0.10, "gesture": 0.05, "turn": 0.05, "side": 0.00, "right": 0.00},
    }
    
    def __init__(self):
        self.action_types: Dict[str, str] = {}  # 动作label -> 类型
        self.transitions: Dict[str, Dict[str, float]] = {}
    
    def build_from_actions(self, actions: List) -> None:
        """从动作列表构建转移矩阵"""
        for action in actions:
            self.action_types[action.label] = action.type
        
        # 构建具体动作的转移矩阵
        for from_action in actions:
            from_type = from_action.type
            self.transitions[from_action.label] = {}
            
            type_probs = self.TYPE_TRANSITIONS.get(from_type, self.TYPE_TRANSITIONS["stand"])
            
            for to_action in actions:
                to_type = to_action.type
                base_prob = type_probs.get(to_type, 0.1)
                
                # 添加随机性
                noise = random.uniform(-0.05, 0.05)
                final_prob = max(0.01, base_prob + noise)
                self.transitions[from_action.label][to_action.label] = final_prob
            
            # 归一化概率
            total = sum(self.transitions[from_action.label].values())
            for to_label in self.transitions[from_action.label]:
                self.transitions[from_action.label][to_label] /= total
        
        logger.debug(f"马尔可夫转移矩阵构建完成，{len(self.transitions)} 个状态")
    
    def get_transition_probs(self, from_action: str) -> Dict[str, float]:
        """获取从指定动作出发的转移概率"""
        return self.transitions.get(from_action, {})


class Choreographer:
    """
    智能编舞器
    
    功能：
    - 根据音乐特征选择合适的动作
    - 使用马尔可夫链保证动作连贯性
    - 考虑节拍对齐和动作多样性
    """
    
    def __init__(self, action_library=None, beat_tracker: BeatTracker = None):
        """
        初始化编舞器
        
        Args:
            action_library: 动作库实例
            beat_tracker: 节拍跟踪器实例
        """
        self.action_library = action_library
        self.beat_tracker = beat_tracker
        self.markov_chain = MarkovChain()
        
        # 配置
        config = dance_config.choreography
        self.music_weight = config.music_weight
        self.coherence_weight = config.coherence_weight
        self.temperature = config.temperature
        self.diversity_penalty = config.diversity_penalty
        self.max_repeat = config.max_repeat_count
        
        # 状态
        self.current_action: Optional[str] = None
        self.action_history: List[str] = []
        self.max_history = config.history_length
        
        # 如果有动作库，构建转移矩阵
        if action_library:
            self._initialize(action_library)
    
    def _initialize(self, action_library) -> None:
        """初始化编舞器"""
        self.action_library = action_library
        self.markov_chain.build_from_actions(action_library.get_all_actions())
        logger.info(f"编舞器初始化完成，动作库: {len(action_library.get_all_actions())}个动作")
    
    def set_action_library(self, action_library) -> None:
        """设置动作库"""
        self._initialize(action_library)
    
    def reset(self) -> None:
        """重置编舞器状态"""
        self.current_action = None
        self.action_history.clear()
        logger.debug("编舞器状态已重置")
    
    def select_action(
        self,
        music_features: MusicFeatures,
        remaining_time_ms: float,
        available_actions: List = None,
    ) -> Optional[Tuple[str, dict, str]]:
        """
        选择下一个动作
        
        Args:
            music_features: 音乐特征
            remaining_time_ms: 剩余时间（毫秒）
            available_actions: 可用动作列表（可选，默认使用全部）
        
        Returns:
            (动作label, 动作数据, 选择理由) 或 None
        """
        if not self.action_library:
            logger.warning("动作库未设置")
            return None
        
        # 获取可用动作（时间内可完成的）
        if available_actions is None:
            available_actions = [
                action for action in self.action_library.get_all_actions()
                if action.time_ms <= remaining_time_ms
            ]
        
        if not available_actions:
            logger.debug("没有可用动作（时间不足）")
            return None
        
        # 计算各动作的综合得分
        scores = []
        for action in available_actions:
            score = self._calculate_action_score(action, music_features)
            scores.append((action, score))
        
        # 排序并选择
        scores.sort(key=lambda x: x[1], reverse=True)
        selected = self._weighted_random_selection(scores)
        
        if selected:
            # 更新状态
            self.current_action = selected.label
            self.action_history.append(selected.label)
            if len(self.action_history) > self.max_history:
                self.action_history.pop(0)
            
            # 获取动作数据
            action_data = self.action_library.get_action_data(selected.label)
            
            # 生成选择理由
            reason = self._generate_reason(selected, music_features, scores)
            
            return selected.label, action_data, reason
        
        return None
    
    def _calculate_action_score(self, action, music_features: MusicFeatures) -> float:
        """计算动作的综合得分"""
        # 音乐匹配得分
        music_score = self._calculate_music_score(action, music_features)
        
        # 马尔可夫连贯性得分
        coherence_score = self._calculate_coherence_score(action)
        
        # 多样性惩罚
        diversity_score = self._calculate_diversity_score(action)
        
        # 节拍对齐得分
        beat_alignment_score = self._calculate_beat_alignment_score(
            action, music_features.get_beat_interval_ms()
        )
        
        # 综合得分
        final_score = (
            music_score * self.music_weight +
            coherence_score * self.coherence_weight * 0.4 +
            beat_alignment_score * self.coherence_weight * 0.4 +
            diversity_score * self.coherence_weight * 0.2
        )
        
        return final_score
    
    def _calculate_music_score(self, action, music_features: MusicFeatures) -> float:
        """计算音乐匹配得分"""
        score = 0.0
        
        # 节奏匹配 (30%)
        tempo_score = self._score_tempo_match(action, music_features)
        score += tempo_score * 0.3
        
        # 能量匹配 (25%)
        energy_score = self._score_energy_match(action, music_features)
        score += energy_score * 0.25
        
        # 情绪匹配 (20%)
        mood_score = self._score_mood_match(action, music_features)
        score += mood_score * 0.2
        
        # 结构匹配 (15%)
        structure_score = self._score_structure_match(action, music_features)
        score += structure_score * 0.15
        
        # 基础分 (10%)
        score += 0.1
        
        return score
    
    def _score_tempo_match(self, action, music_features: MusicFeatures) -> float:
        """节奏匹配评分"""
        if not hasattr(action, 'tempo_match') or action.tempo_match == "any":
            return 0.8
        
        if music_features.tempo > 140:
            return 1.0 if action.tempo_match == "fast" else 0.3
        elif music_features.tempo < 80:
            return 1.0 if action.tempo_match == "slow" else 0.3
        else:
            return 1.0 if action.tempo_match == "medium" else 0.6
    
    def _score_energy_match(self, action, music_features: MusicFeatures) -> float:
        """能量匹配评分"""
        if not hasattr(action, 'energy'):
            return 0.7
        
        if music_features.energy > 0.5:
            return 1.0 if action.energy == "high" else 0.4
        elif music_features.energy < 0.2:
            return 1.0 if action.energy == "low" else 0.4
        else:
            return 1.0 if action.energy == "medium" else 0.7
    
    def _score_mood_match(self, action, music_features: MusicFeatures) -> float:
        """情绪匹配评分"""
        if music_features.mood == "energetic":
            return 1.0 if hasattr(action, 'type') and action.type in ["forward", "combo", "dance", "left", "right"] else 0.5
        elif music_features.mood == "calm":
            return 1.0 if hasattr(action, 'type') and action.type in ["stand", "gesture"] else 0.5
        return 0.7
    
    def _score_structure_match(self, action, music_features: MusicFeatures) -> float:
        """结构匹配评分"""
        segment = music_features.segment_type
        if segment == "unknown":
            return 0.7
        
        if not hasattr(action, 'type'):
            return 0.7
        
        # 不同段落偏好不同类型的动作
        preferences = {
            "intro": ["stand", "gesture"],
            "verse": ["forward", "side", "left", "right"],
            "chorus": ["combo", "forward", "dance"],
            "bridge": ["turn", "side", "left", "right", "dance"],
            "outro": ["stand", "gesture"],
        }
        
        preferred = preferences.get(segment, [])
        return 1.0 if action.type in preferred else 0.5
    
    def _calculate_coherence_score(self, action) -> float:
        """计算连贯性得分"""
        if not self.current_action:
            return 0.5
        
        probs = self.markov_chain.get_transition_probs(self.current_action)
        return probs.get(action.label, 0.1)
    
    def _calculate_diversity_score(self, action) -> float:
        """计算多样性得分"""
        if not self.action_history:
            return 1.0
        
        recent = self.action_history[-5:]
        repeat_count = recent.count(action.label)
        
        if repeat_count == 0:
            return 1.0
        elif repeat_count == 1:
            return 0.7
        elif repeat_count >= self.max_repeat:
            return 0.1
        else:
            return 0.3
    
    def _calculate_beat_alignment_score(self, action, beat_interval_ms: float) -> float:
        """
        计算动作时长与节拍周期的对齐分数
        
        理想情况：动作时长是节拍周期的整数倍
        """
        if beat_interval_ms <= 0:
            return 0.5
        
        action_duration = action.time_ms
        beat_count = round(action_duration / beat_interval_ms)
        
        if beat_count == 0:
            beat_count = 1
        
        ideal_duration = beat_count * beat_interval_ms
        alignment_error = abs(action_duration - ideal_duration) / action_duration
        
        return max(0.1, 1.0 - alignment_error)
    
    def _weighted_random_selection(self, scored_actions: List) -> Optional[object]:
        """加权随机选择"""
        if not scored_actions:
            return None
        
        # 使用 softmax 温度调节
        scores = [score for _, score in scored_actions]
        scaled = [s / self.temperature for s in scores]
        max_s = max(scaled)
        exp_scores = [np.exp(s - max_s) for s in scaled]
        total = sum(exp_scores)
        probs = [e / total for e in exp_scores]
        
        # 随机选择
        rand = random.random()
        cumulative = 0
        for i, p in enumerate(probs):
            cumulative += p
            if rand <= cumulative:
                return scored_actions[i][0]
        
        return scored_actions[0][0]
    
    def _generate_reason(self, action, music_features: MusicFeatures, scores: List) -> str:
        """生成选择理由"""
        reasons = []
        
        # 音乐相关
        if music_features.tempo > 140:
            reasons.append("快节奏音乐")
        elif music_features.tempo < 80:
            reasons.append("慢节奏音乐")
        
        if music_features.mood == "energetic":
            reasons.append("高能量氛围")
        elif music_features.mood == "calm":
            reasons.append("平静氛围")
        
        # 动作类型
        if hasattr(action, 'type'):
            type_names = {
                "stand": "稳定姿态",
                "forward": "前进动作",
                "turn": "转向动作",
                "side": "侧移动作",
                "gesture": "手势动作",
                "combo": "组合动作",
                "dance": "舞蹈动作",
                "left": "左移动作",
                "right": "右移动作",
            }
            reasons.append(type_names.get(action.type, action.type))
        
        # 连贯性
        if self.current_action:
            reasons.append("动作连贯")
        
        return "，".join(reasons) if reasons else "综合评分最优"
    
    def get_status(self) -> dict:
        """获取编舞器状态"""
        return {
            "current_action": self.current_action,
            "history_length": len(self.action_history),
            "recent_actions": self.action_history[-5:] if self.action_history else [],
            "music_weight": self.music_weight,
            "coherence_weight": self.coherence_weight,
        }
