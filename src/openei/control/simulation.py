from __future__ import annotations

from dataclasses import dataclass, field

from ..contracts import ControlCommand, RuntimeContext
from ..ports import ControlAdapter


@dataclass(slots=True)
class SimulationControlAdapter(ControlAdapter):
    name: str = "simulation"
    history: list[dict[str, object]] = field(default_factory=list)
    is_dancing: bool = False
    last_action: str | None = None

    def execute(self, command: ControlCommand, context: RuntimeContext) -> tuple[bool, str]:
        payload: dict[str, object] = {key: value for key, value in command.payload.items()}
        entry: dict[str, object] = {
            "command_type": command.command_type,
            "payload": payload,
        }
        self.history.append(entry)

        if command.command_type == "start_dance":
            duration = command.payload.get("duration_seconds")
            self.is_dancing = True
            self.last_action = f"dance:{duration}"
            return True, f"[sim] 开始跳舞 {duration} 秒。"

        if command.command_type == "stop_dance":
            self.is_dancing = False
            self.last_action = "stop"
            return True, "[sim] 已停止跳舞。"

        if command.command_type == "execute_action":
            label = str(command.payload.get("action_label", ""))
            self.last_action = label
            return True, f"[sim] 已执行动作 {label}。"

        return False, f"[sim] 不支持的控制命令：{command.command_type}"

    def inspect(self) -> dict[str, object]:
        return {
            "mode": self.name,
            "is_dancing": self.is_dancing,
            "last_action": self.last_action,
            "history_size": len(self.history),
            "pending_action": None,
        }
