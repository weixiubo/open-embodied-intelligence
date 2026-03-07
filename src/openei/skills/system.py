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
            text = request.step.parameters.get("text", "")
            return SkillResult(
                success=True,
                messages=(
                    f"OpenEI Phase 1 当前优先处理结构化机器人命令。收到内容：{text}",
                ),
            )
        if action == "exit":
            return SkillResult(success=True, messages=("OpenEI 正在退出。",), should_exit=True)
        if action == "confirm_pending":
            return SkillResult(success=True)
        if action == "cancel_pending":
            return SkillResult(success=True)
        return SkillResult(success=False, messages=(f"不支持的系统操作：{action}",))

    def _render_status(self, status: dict[str, object]) -> str:
        mode = status.get("mode", "unknown")
        dancing = "跳舞中" if status.get("is_dancing") else "待机"
        pending = status.get("pending_action")
        suffix = f"，待确认任务：{pending}" if pending else ""
        return f"OpenEI 当前处于{dancing}，控制模式为 {mode}{suffix}。"
