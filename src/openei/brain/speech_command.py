from __future__ import annotations

import re
from collections.abc import Iterable

from ..contracts import (
    IntentKind,
    PerceptionEvent,
    RuntimeContext,
    StructuredIntent,
    TaskPlan,
    TaskStep,
)
from ..logging import get_logger
from ..ports import Brain

logger = get_logger("brain")

CONFIRM_WORDS = ("是", "确认", "对", "好的", "可以", "没错", "开始吧")
CANCEL_WORDS = ("不是", "取消", "算了", "不用", "不对", "否")
EXIT_WORDS = ("退出", "结束对话", "再见", "关闭系统")
STATUS_WORDS = ("机器人状态", "舞蹈状态", "现在状态")
LIST_WORDS = ("舞蹈列表", "动作列表", "有什么舞蹈")
STOP_WORDS = ("停止跳舞", "停止舞蹈", "不跳了")
DANCE_WORDS = ("跳舞", "舞蹈", "跳")
ACTION_WORDS = ("执行动作", "做动作")

_CN_BASIC = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}

HIGH_RISK_DURATION_SECONDS = 30
MIN_DURATION_SECONDS = 5
MAX_DURATION_SECONDS = 60


def normalize_speech_text(text: str) -> str:
    normalized = text.strip().lower()
    normalized = normalized.replace("秒钟", "秒")
    normalized = re.sub(r"(\d+)\s*(s|sec|seconds?)\b", r"\1秒", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    normalized = normalized.replace("确认一下", "确认")
    normalized = normalized.replace("开始跳舞", "跳舞")
    normalized = normalized.replace("开始舞蹈", "跳舞")
    return normalized


def _cn_to_int(text: str) -> int | None:
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if len(text) == 1:
        return _CN_BASIC.get(text)
    if text[0] == "十":
        ones = _CN_BASIC.get(text[1], 0) if len(text) > 1 else 0
        return 10 + ones
    if len(text) >= 2 and text[1] == "十":
        tens = _CN_BASIC.get(text[0])
        if tens is None:
            return None
        ones = _CN_BASIC.get(text[2], 0) if len(text) > 2 else 0
        return tens * 10 + ones
    return None


def extract_duration_candidates(text: str) -> list[int]:
    normalized = normalize_speech_text(text)
    results: list[int] = []

    for match in re.findall(r"(\d+)\s*秒", normalized):
        results.append(int(match))

    cn_pattern = (
        r"(十[一二三四五六七八九]?|"
        r"[一二三四五六七八九两]十[一二三四五六七八九]?|"
        r"[一二三四五六七八九两])秒"
    )
    for match in re.findall(cn_pattern, normalized):
        value = _cn_to_int(match)
        if value is not None:
            results.append(value)

    deduped: list[int] = []
    seen: set[int] = set()
    for value in results:
        if value not in seen:
            seen.add(value)
            deduped.append(value)
    return deduped


class SpeechCommandBrain(Brain):
    def __init__(self, dance_action_labels: Iterable[str]) -> None:
        self._dance_action_labels = [normalize_speech_text(label) for label in dance_action_labels]

    def plan(self, event: PerceptionEvent, context: RuntimeContext) -> TaskPlan | None:
        raw_text = event.raw_text.strip()
        if not raw_text:
            return None

        normalized = event.normalized_text or normalize_speech_text(raw_text)
        matched_action = next((label for label in self._dance_action_labels if label in normalized), None)

        if any(word in normalized for word in CANCEL_WORDS):
            return self._plan(IntentKind.CANCEL, raw_text, normalized, "system", "cancel_pending", "取消待确认任务")
        if any(word in normalized for word in EXIT_WORDS):
            return self._plan(IntentKind.EXIT, raw_text, normalized, "system", "exit", "退出 OpenEI")
        if any(word in normalized for word in CONFIRM_WORDS):
            return self._plan(IntentKind.CONFIRM, raw_text, normalized, "system", "confirm_pending", "确认待确认任务")
        if any(word in normalized for word in STOP_WORDS):
            return self._plan(IntentKind.STOP, raw_text, normalized, "dance", "stop_dance", "停止跳舞")
        if any(word in normalized for word in STATUS_WORDS):
            return self._plan(IntentKind.STATUS, raw_text, normalized, "system", "status", "查看运行状态")
        if any(word in normalized for word in LIST_WORDS):
            return self._plan(IntentKind.LIST_ACTIONS, raw_text, normalized, "dance", "list_actions", "查看动作列表")

        if matched_action and any(word in normalized for word in ACTION_WORDS):
            return self._plan(
                IntentKind.ACTION,
                raw_text,
                normalized,
                "dance",
                "execute_action",
                f"执行动作 {matched_action}",
                action_label=matched_action,
            )

        duration_candidates = extract_duration_candidates(normalized)
        has_dance_keyword = any(word in normalized for word in DANCE_WORDS)
        inferred_dance = bool(duration_candidates) and "秒" in normalized and any(
            token in normalized for token in ("要", "给我")
        )

        if matched_action and not has_dance_keyword and not duration_candidates:
            return self._plan(
                IntentKind.ACTION,
                raw_text,
                normalized,
                "dance",
                "execute_action",
                f"执行动作 {matched_action}",
                action_label=matched_action,
            )

        if has_dance_keyword or inferred_dance:
            risks: list[str] = []
            if len(duration_candidates) > 1:
                risks.append("multiple_durations")
            if inferred_dance and not has_dance_keyword:
                risks.append("inferred_command")

            duration = duration_candidates[0] if duration_candidates else None
            if duration is None:
                risks.append("missing_duration")
            else:
                if duration > HIGH_RISK_DURATION_SECONDS:
                    risks.append("long_duration")
                if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
                    risks.append("out_of_range")

            summary = "跳舞" if duration is None else f"跳舞 {duration} 秒"
            intent = StructuredIntent(
                kind=IntentKind.DANCE,
                skill_name="dance",
                raw_text=raw_text,
                normalized_text=normalized,
                parameters={"duration_seconds": duration},
                confidence=0.92 if has_dance_keyword else 0.72,
                risk_flags=tuple(risks),
                delegation_hints=("skill:dance",),
            )
            step = TaskStep(skill_name="dance", action="start_dance", parameters=intent.parameters, summary=summary)
            return TaskPlan(
                intent=intent,
                steps=(step,),
                summary=summary,
                delegation_enabled=False,
                delegation_candidates=("skill:dance",),
            )

        logger.debug("No structured command matched, falling back to system chat.")
        return self._plan(
            IntentKind.CHAT,
            raw_text,
            normalized,
            "system",
            "chat_fallback",
            "聊天回退",
            text=raw_text,
        )

    def _plan(
        self,
        kind: IntentKind,
        raw_text: str,
        normalized_text: str,
        skill_name: str,
        action: str,
        summary: str,
        **parameters: object,
    ) -> TaskPlan:
        intent = StructuredIntent(
            kind=kind,
            skill_name=skill_name,
            raw_text=raw_text,
            normalized_text=normalized_text,
            parameters=parameters,
            delegation_hints=(f"skill:{skill_name}",),
        )
        step = TaskStep(skill_name=skill_name, action=action, parameters=parameters, summary=summary)
        return TaskPlan(
            intent=intent,
            steps=(step,),
            summary=summary,
            delegation_enabled=False,
            delegation_candidates=(f"skill:{skill_name}",),
        )
