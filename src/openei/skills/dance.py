from __future__ import annotations

from typing import Protocol

from ..contracts import ControlCommand, RuntimeContext, SkillRequest, SkillResult
from ..ports import Skill


class DanceCatalog(Protocol):
    def action_labels(self) -> list[str]:
        ...

    def has_action(self, label: str) -> bool:
        ...

    def render_action_list(self) -> str:
        ...


class DanceSkill(Skill):
    name = "dance"
    description = "Dance execution and motion-oriented capabilities."

    def __init__(self, catalog: DanceCatalog) -> None:
        self.catalog = catalog

    def execute(self, request: SkillRequest, context: RuntimeContext) -> SkillResult:
        action = request.step.action
        parameters = request.step.parameters

        if action == "list_actions":
            return SkillResult(success=True, messages=(self.catalog.render_action_list(),))

        if action == "execute_action":
            label = str(parameters.get("action_label", ""))
            if not self.catalog.has_action(label):
                return SkillResult(success=False, messages=(f"未找到动作 {label}。",))
            return SkillResult(
                success=True,
                emitted_commands=(
                    ControlCommand(
                        adapter="dance",
                        command_type="execute_action",
                        payload={"action_label": label},
                    ),
                ),
            )

        if action == "start_dance":
            duration = parameters.get("duration_seconds")
            return SkillResult(
                success=True,
                emitted_commands=(
                    ControlCommand(
                        adapter="dance",
                        command_type="start_dance",
                        payload={"duration_seconds": duration},
                    ),
                ),
            )

        if action == "stop_dance":
            return SkillResult(
                success=True,
                emitted_commands=(
                    ControlCommand(adapter="dance", command_type="stop_dance"),
                ),
            )

        return SkillResult(success=False, messages=(f"不支持的舞蹈动作操作：{action}",))
