from __future__ import annotations

from openei.control.simulation import SimulationControlAdapter
from openei.skills.announce import AnnounceSkill
from openei.skills.registry import SkillRegistry
from openei.skills.system import SystemSkill


def test_registry_describes_registered_skills() -> None:
    registry = SkillRegistry()
    registry.register_many(
        (
            AnnounceSkill(),
            SystemSkill(control=SimulationControlAdapter()),
        )
    )

    descriptors = registry.describe()

    assert [descriptor.to_dict() for descriptor in descriptors] == [
        {
            "name": "announce",
            "description": "A non-motion skill for spoken notices, scripted lines, and user-facing feedback.",
        },
        {
            "name": "system",
            "description": "Runtime status, help text, and graceful exit handling.",
        },
    ]
