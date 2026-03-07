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

SECOND = "\u79d2"
SECOND_CLOCK = "\u79d2\u949f"
NON_ZERO_CN_NUMERALS = "\u4e00\u4e8c\u4e24\u4e09\u56db\u4e94\u516d\u4e03\u516b\u4e5d"
ALL_CN_NUMERALS = "\u96f6\u3007" + NON_ZERO_CN_NUMERALS

CONFIRM_WORDS = (
    "\u662f",
    "\u786e\u8ba4",
    "\u5bf9",
    "\u597d\u7684",
    "\u53ef\u4ee5",
    "\u6ca1\u9519",
    "\u5f00\u59cb\u5427",
    "confirm",
    "yes",
    "ok",
)
CANCEL_WORDS = (
    "\u4e0d\u662f",
    "\u53d6\u6d88",
    "\u7b97\u4e86",
    "\u4e0d\u7528",
    "\u4e0d\u5bf9",
    "\u5426",
    "cancel",
    "no",
)
EXIT_WORDS = (
    "\u9000\u51fa",
    "\u7ed3\u675f\u5bf9\u8bdd",
    "\u518d\u89c1",
    "\u5173\u95ed\u7cfb\u7edf",
    "exit",
    "quit",
)
STATUS_WORDS = (
    "\u673a\u5668\u4eba\u72b6\u6001",
    "\u821e\u8e48\u72b6\u6001",
    "\u73b0\u5728\u72b6\u6001",
    "status",
)
LIST_WORDS = (
    "\u821e\u8e48\u5217\u8868",
    "\u52a8\u4f5c\u5217\u8868",
    "\u6709\u4ec0\u4e48\u821e\u8e48",
    "listactions",
)
STOP_WORDS = (
    "\u505c\u6b62\u8df3\u821e",
    "\u505c\u6b62\u821e\u8e48",
    "\u4e0d\u8df3\u4e86",
    "stopdance",
    "stop",
)
DANCE_WORDS = (
    "\u8df3\u821e",
    "\u821e\u8e48",
    "\u8df3",
    "dance",
)
ACTION_WORDS = (
    "\u6267\u884c\u52a8\u4f5c",
    "\u505a\u52a8\u4f5c",
    "action",
)
ANNOUNCE_WORDS = (
    "\u64ad\u62a5",
    "\u6717\u8bfb",
    "\u63d0\u9192\u5927\u5bb6",
    "announce",
    "say",
)
INFERRED_DANCE_TOKENS = ("\u8981", "\u7ed9\u6211")

CN_DIGITS = {
    "\u96f6": 0,
    "\u3007": 0,
    "\u4e00": 1,
    "\u4e8c": 2,
    "\u4e24": 2,
    "\u4e09": 3,
    "\u56db": 4,
    "\u4e94": 5,
    "\u516d": 6,
    "\u4e03": 7,
    "\u516b": 8,
    "\u4e5d": 9,
}
CN_TEN = "\u5341"

HIGH_RISK_DURATION_SECONDS = 30
MIN_DURATION_SECONDS = 5
MAX_DURATION_SECONDS = 60


def normalize_speech_text(text: str) -> str:
    normalized = text.strip().lower()
    normalized = normalized.replace(SECOND_CLOCK, SECOND)
    normalized = re.sub(r"(\d+)\s*(s|sec|secs|seconds?)\b", rf"\1{SECOND}", normalized)
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(r"[,.!?;\u3002\uff0c\uff01\uff1f\uff1b]", "", normalized)
    normalized = normalized.replace("\u786e\u8ba4\u4e00\u4e0b", "\u786e\u8ba4")
    normalized = normalized.replace("\u5f00\u59cb\u8df3\u821e", "\u8df3\u821e")
    normalized = normalized.replace("\u5f00\u59cb\u821e\u8e48", "\u8df3\u821e")
    return normalized


def _cn_to_int(text: str) -> int | None:
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if len(text) == 1:
        return CN_DIGITS.get(text)
    if text[0] == CN_TEN:
        ones = CN_DIGITS.get(text[1], 0) if len(text) > 1 else 0
        return 10 + ones
    if len(text) >= 2 and text[1] == CN_TEN:
        tens = CN_DIGITS.get(text[0])
        if tens is None:
            return None
        ones = CN_DIGITS.get(text[2], 0) if len(text) > 2 else 0
        return tens * 10 + ones
    return None


def extract_duration_candidates(text: str) -> list[int]:
    normalized = normalize_speech_text(text)
    results: list[int] = []

    for match in re.findall(rf"(\d+){SECOND}", normalized):
        results.append(int(match))

    cn_pattern = rf"((?:{CN_TEN}[{ALL_CN_NUMERALS}]?|[{NON_ZERO_CN_NUMERALS}]{CN_TEN}[{ALL_CN_NUMERALS}]?|[{ALL_CN_NUMERALS}])){SECOND}"
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


def extract_announcement_text(text: str) -> str | None:
    normalized = normalize_speech_text(text)
    for prefix in ANNOUNCE_WORDS:
        if normalized.startswith(prefix):
            payload = normalized.removeprefix(prefix).strip()
            return payload or None
    return None


class DeterministicSpeechBrain(Brain):
    def __init__(self, dance_action_labels: Iterable[str]) -> None:
        self._dance_action_labels = [normalize_speech_text(label) for label in dance_action_labels]

    def plan(self, event: PerceptionEvent, context: RuntimeContext) -> TaskPlan | None:
        raw_text = event.raw_text.strip()
        if not raw_text:
            return None

        normalized = event.normalized_text or normalize_speech_text(raw_text)
        matched_action = next((label for label in self._dance_action_labels if label in normalized), None)

        if any(word in normalized for word in CANCEL_WORDS):
            return self._plan(IntentKind.CANCEL, raw_text, normalized, "system", "cancel_pending", "Cancel pending request.")
        if any(word in normalized for word in EXIT_WORDS):
            return self._plan(IntentKind.EXIT, raw_text, normalized, "system", "exit", "Exit OpenEI.")
        if any(word in normalized for word in CONFIRM_WORDS):
            return self._plan(IntentKind.CONFIRM, raw_text, normalized, "system", "confirm_pending", "Confirm pending request.")
        if any(word in normalized for word in STOP_WORDS):
            return self._plan(IntentKind.STOP, raw_text, normalized, "dance", "stop_dance", "Stop dance.")
        if any(word in normalized for word in STATUS_WORDS):
            return self._plan(IntentKind.STATUS, raw_text, normalized, "system", "status", "Inspect runtime status.")
        if any(word in normalized for word in LIST_WORDS):
            return self._plan(IntentKind.LIST_ACTIONS, raw_text, normalized, "dance", "list_actions", "List available dance actions.")

        announcement = extract_announcement_text(raw_text)
        if announcement is not None:
            return self._plan(
                IntentKind.ANNOUNCE,
                raw_text,
                normalized,
                "announce",
                "announce_text",
                f"Announce: {announcement}",
                text=announcement,
            )

        if matched_action and any(word in normalized for word in ACTION_WORDS):
            return self._plan(
                IntentKind.ACTION,
                raw_text,
                normalized,
                "dance",
                "execute_action",
                f"Execute action {matched_action}.",
                action_label=matched_action,
            )

        duration_candidates = extract_duration_candidates(normalized)
        has_dance_keyword = any(word in normalized for word in DANCE_WORDS)
        inferred_dance = bool(duration_candidates) and SECOND in normalized and any(
            token in normalized for token in INFERRED_DANCE_TOKENS
        )

        if matched_action and not has_dance_keyword and not duration_candidates:
            return self._plan(
                IntentKind.ACTION,
                raw_text,
                normalized,
                "dance",
                "execute_action",
                f"Execute action {matched_action}.",
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

            summary = "Start dance." if duration is None else f"Start dance for {duration} seconds."
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
                metadata={"brain_mode": "deterministic"},
            )

        logger.debug("No structured command matched; falling back to system chat.")
        return self._plan(
            IntentKind.CHAT,
            raw_text,
            normalized,
            "system",
            "chat_fallback",
            "Handle chat fallback.",
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
            metadata={"brain_mode": "deterministic"},
        )
