from __future__ import annotations

from openei.config import OpenEISettings
from openei.contracts import (
    IntentKind,
    PerceptionEvent,
    RuntimeContext,
    SkillRequest,
    StructuredIntent,
    TaskPlan,
    TaskStep,
)
from openei.skills.announce import AnnounceSkill


def test_announce_skill_returns_feedback_message() -> None:
    skill = AnnounceSkill()
    event = PerceptionEvent(
        source="test",
        modality="speech",
        raw_text="\u64ad\u62a5OpenEI\u51c6\u5907\u597d\u4e86",
        normalized_text="\u64ad\u62a5openei\u51c6\u5907\u597d\u4e86",
    )
    intent = StructuredIntent(
        kind=IntentKind.ANNOUNCE,
        skill_name="announce",
        raw_text=event.raw_text,
        normalized_text=event.normalized_text,
        parameters={"text": "OpenEI\u51c6\u5907\u597d\u4e86"},
    )
    step = TaskStep(skill_name="announce", action="announce_text", parameters={"text": "OpenEI\u51c6\u5907\u597d\u4e86"})
    request = SkillRequest(
        event=event,
        intent=intent,
        plan=TaskPlan(intent=intent, steps=(step,), summary="Announce OpenEI ready."),
        step=step,
    )

    result = skill.execute(request, RuntimeContext(settings=OpenEISettings()))

    assert result.success is True
    assert result.messages == ("Announcement: OpenEI\u51c6\u5907\u597d\u4e86",)
