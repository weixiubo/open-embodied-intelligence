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
        raw_text="播报OpenEI准备好了",
        normalized_text="播报openei准备好了",
    )
    intent = StructuredIntent(
        kind=IntentKind.ANNOUNCE,
        skill_name="announce",
        raw_text=event.raw_text,
        normalized_text=event.normalized_text,
        parameters={"text": "OpenEI准备好了"},
    )
    step = TaskStep(skill_name="announce", action="announce_text", parameters={"text": "OpenEI准备好了"})
    request = SkillRequest(
        event=event,
        intent=intent,
        plan=TaskPlan(intent=intent, steps=(step,), summary="播报：OpenEI准备好了"),
        step=step,
    )

    result = skill.execute(request, RuntimeContext(settings=OpenEISettings()))

    assert result.success is True
    assert result.messages == ("播报内容：OpenEI准备好了",)
