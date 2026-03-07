from __future__ import annotations

from openei.config import OpenEISettings
from openei.contracts import ControlCommand, RuntimeContext
from openei.control.simulation import SimulationControlAdapter


def test_simulation_control_tracks_dance_state() -> None:
    adapter = SimulationControlAdapter()
    context = RuntimeContext(settings=OpenEISettings())

    ok, _ = adapter.execute(
        ControlCommand(adapter="dance", command_type="start_dance", payload={"duration_seconds": 10}),
        context,
    )

    assert ok is True
    assert adapter.inspect()["is_dancing"] is True

    ok, _ = adapter.execute(ControlCommand(adapter="dance", command_type="stop_dance"), context)

    assert ok is True
    assert adapter.inspect()["is_dancing"] is False

