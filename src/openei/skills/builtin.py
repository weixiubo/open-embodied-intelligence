from __future__ import annotations

from collections.abc import Iterable

from ..ports import ControlAdapter, Skill
from .announce import AnnounceSkill
from .dance import DanceCatalog, DanceSkill
from .system import SystemSkill


def build_builtin_skills(
    *,
    dance_catalog: DanceCatalog,
    control: ControlAdapter,
) -> tuple[Skill, ...]:
    skills: Iterable[Skill] = (
        AnnounceSkill(),
        DanceSkill(catalog=dance_catalog),
        SystemSkill(control=control),
    )
    return tuple(skills)
