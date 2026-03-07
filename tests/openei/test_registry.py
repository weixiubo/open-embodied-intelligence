from __future__ import annotations

from openei.control.simulation import SimulationControlAdapter
from openei.skills.registry import SkillRegistry
from openei.skills.system import SystemSkill


def test_registry_describes_registered_skills() -> None:
    registry = SkillRegistry()
    registry.register(SystemSkill(control=SimulationControlAdapter()))

    descriptors = registry.describe()

    assert descriptors == [
        {
            "name": "system",
            "description": "Runtime status, help text, and graceful exit handling.",
        }
    ]

