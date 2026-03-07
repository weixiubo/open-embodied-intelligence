from __future__ import annotations

from ..contracts import RuntimeContext, SkillRequest, SkillResult
from ..ports import ControlAdapter, Skill


class SystemSkill(Skill):
    name = "system"
    description = "Runtime status, help text, and graceful exit handling."

    def __init__(self, control: ControlAdapter) -> None:
        self.control = control

    def execute(self, request: SkillRequest, context: RuntimeContext) -> SkillResult:
        action = request.step.action
        if action == "status":
            status = self.control.inspect()
            return SkillResult(success=True, messages=(self._render_status(status),))
        if action == "chat_fallback":
            text = str(request.step.parameters.get("text", ""))
            return SkillResult(
                success=True,
                messages=(
                    f"OpenEI Phase 1 is prioritizing structured robot commands. Received chat fallback: {text}",
                ),
            )
        if action == "exit":
            return SkillResult(success=True, messages=("OpenEI is shutting down.",), should_exit=True)
        if action in {"confirm_pending", "cancel_pending"}:
            return SkillResult(success=True)
        return SkillResult(success=False, messages=(f"Unsupported system action: {action}",))

    def _render_status(self, status: dict[str, object]) -> str:
        mode = status.get("mode", "unknown")
        dancing = "dancing" if status.get("is_dancing") else "idle"
        pending = status.get("pending_action")
        suffix = f", pending_action={pending}" if pending else ""
        return f"OpenEI status: state={dancing}, transport={mode}{suffix}"
