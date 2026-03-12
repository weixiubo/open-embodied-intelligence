"""
语音意图解析。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Optional

from utils.helpers import extract_duration_candidates, normalize_voice_text


class VoiceIntentType(str, Enum):
    DANCE = "dance"
    STOP = "stop"
    ACTION = "action"
    LIST_ACTIONS = "list_actions"
    STATUS = "status"
    EXIT = "exit"
    CONFIRM = "confirm"
    CANCEL = "cancel"
    CHAT = "chat"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VoiceIntent:
    kind: VoiceIntentType
    original_text: str
    normalized_text: str
    duration_seconds: Optional[int] = None
    action_label: Optional[str] = None
    requires_confirmation: bool = False
    risk_flags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_high_risk(self) -> bool:
        return bool(self.risk_flags)


CONFIRM_WORDS = ("是", "确认", "对", "好的", "可以", "没错", "开始吧")
CANCEL_WORDS = ("不是", "取消", "算了", "不用", "不对", "否")
EXIT_WORDS = ("退出", "结束对话", "再见", "关闭系统")
STATUS_WORDS = ("机器人状态", "舞蹈状态", "现在状态")
LIST_WORDS = ("舞蹈列表", "动作列表", "有什么舞蹈")
STOP_WORDS = ("停止跳舞", "停止舞蹈", "不跳了")
DANCE_WORDS = ("跳舞", "舞蹈", "跳")
ACTION_WORDS = ("执行动作", "做动作")


def parse_voice_intent(
    text: str,
    action_labels: Optional[Iterable[str]] = None,
    confirm_dance_commands: bool = False,
    confirm_high_risk_only: bool = True,
) -> VoiceIntent:
    normalized = normalize_voice_text(text)
    action_labels = list(action_labels or [])

    if any(word in normalized for word in CANCEL_WORDS):
        return VoiceIntent(VoiceIntentType.CANCEL, text, normalized)
    if any(word in normalized for word in EXIT_WORDS):
        return VoiceIntent(VoiceIntentType.EXIT, text, normalized)
    if any(word in normalized for word in CONFIRM_WORDS):
        return VoiceIntent(VoiceIntentType.CONFIRM, text, normalized)
    if any(word in normalized for word in STOP_WORDS):
        return VoiceIntent(VoiceIntentType.STOP, text, normalized)
    if any(word in normalized for word in STATUS_WORDS):
        return VoiceIntent(VoiceIntentType.STATUS, text, normalized)
    if any(word in normalized for word in LIST_WORDS):
        return VoiceIntent(VoiceIntentType.LIST_ACTIONS, text, normalized)

    matched_action = next((label for label in action_labels if label and label in normalized), None)
    if matched_action and any(word in normalized for word in ACTION_WORDS):
        return VoiceIntent(VoiceIntentType.ACTION, text, normalized, action_label=matched_action)

    duration_candidates = extract_duration_candidates(normalized)
    has_duration = bool(duration_candidates)
    has_dance_keyword = any(word in normalized for word in DANCE_WORDS)
    inferred_dance = has_duration and ("秒" in normalized and ("要" in normalized or "给我" in normalized))

    if matched_action and has_dance_keyword is False and has_duration is False:
        return VoiceIntent(VoiceIntentType.ACTION, text, normalized, action_label=matched_action)

    if has_dance_keyword or inferred_dance:
        duration = duration_candidates[0] if duration_candidates else 15
        risks = []
        if len(duration_candidates) > 1:
            risks.append("multiple_durations")
        if inferred_dance and not has_dance_keyword:
            risks.append("inferred_command")
        if duration > 30:
            risks.append("long_duration")
        if duration < 5 or duration > 60:
            risks.append("out_of_range")
        requires_confirmation = False
        if confirm_dance_commands:
            requires_confirmation = True
        elif confirm_high_risk_only and risks:
            requires_confirmation = True
        return VoiceIntent(
            kind=VoiceIntentType.DANCE,
            original_text=text,
            normalized_text=normalized,
            duration_seconds=duration,
            requires_confirmation=requires_confirmation,
            risk_flags=tuple(risks),
        )

    if matched_action:
        return VoiceIntent(VoiceIntentType.ACTION, text, normalized, action_label=matched_action)

    if normalized:
        return VoiceIntent(VoiceIntentType.CHAT, text, normalized)

    return VoiceIntent(VoiceIntentType.UNKNOWN, text, normalized)
