from __future__ import annotations

from ..contracts import RuntimeContext, SkillRequest, SkillResult
from ..ports import Skill


class AnnounceSkill(Skill):
    name = "announce"
    description = "A non-motion skill for spoken notices, scripted lines, and user-facing feedback."

    def execute(self, request: SkillRequest, context: RuntimeContext) -> SkillResult:
        text = str(request.step.parameters.get("text", "")).strip()
        if not text:
            return SkillResult(success=False, messages=("Provide text to announce.",))
        return SkillResult(
            success=True,
            messages=(f"Announcement: {text}",),
            metadata={"announced_text": text},
        )
