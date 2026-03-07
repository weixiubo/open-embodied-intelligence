from __future__ import annotations

from typing import Any, cast

from ..config import TransportMode as OpenEITransportMode
from ..contracts import ControlCommand, RuntimeContext
from ..ports import ControlAdapter
from ._legacy_imports import ensure_legacy_project_root_on_path


class LegacyDanceCatalog:
    def __init__(self) -> None:
        ensure_legacy_project_root_on_path()
        from dance.action_library import ActionLibrary

        self._library = ActionLibrary()

    def action_labels(self) -> list[str]:
        return cast(list[str], self._library.get_labels())

    def has_action(self, label: str) -> bool:
        return self._library.get_action(label) is not None

    def render_action_list(self) -> str:
        labels = ", ".join(self._library.get_labels())
        return f"Available dance actions: {labels}"


class LegacyDanceControlAdapter(ControlAdapter):
    name = "legacy-dance-control"

    def __init__(self, transport: OpenEITransportMode) -> None:
        ensure_legacy_project_root_on_path()
        from config import RecordingMode as LegacyRecordingMode
        from config import RuntimeProfile as LegacyRuntimeProfile
        from config import TransportMode as LegacyTransportMode
        from config import build_runtime_profile
        from dance.robot_controller import RobotController

        mapped_transport = LegacyTransportMode(transport.value)
        profile = build_runtime_profile(
            LegacyRuntimeProfile.DEMO,
            mapped_transport,
            LegacyRecordingMode.SMART_VAD,
        )
        self._controller: Any = RobotController(profile_config=profile)

    def execute(self, command: ControlCommand, context: RuntimeContext) -> tuple[bool, str]:
        if command.command_type == "start_dance":
            duration = int(command.payload["duration_seconds"])
            ok = self._controller.start_dance(duration)
            return ok, self._controller.pop_feedback_message() or ""

        if command.command_type == "stop_dance":
            self._controller.stop_dance()
            return True, self._controller.pop_feedback_message() or ""

        if command.command_type == "execute_action":
            label = str(command.payload["action_label"])
            ok = self._controller.execute_single_action(label)
            return ok, self._controller.pop_feedback_message() or ""

        return False, f"LegacyDanceControlAdapter does not support command '{command.command_type}'."

    def inspect(self) -> dict[str, object]:
        status = self._controller.get_status()
        pending = status.get("pending_confirmation")
        return {
            "mode": status["serial"]["mode"],
            "is_dancing": status["is_dancing"],
            "pending_action": pending,
            "serial": status["serial"],
        }
