from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..ports import Skill


@dataclass(frozen=True, slots=True)
class SkillDescriptor:
    name: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {
            "name": self.name,
            "description": self.description,
        }


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def register_many(self, skills: Iterable[Skill]) -> None:
        for skill in skills:
            self.register(skill)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def describe(self) -> tuple[SkillDescriptor, ...]:
        return tuple(
            SkillDescriptor(name=skill.name, description=skill.description)
            for skill in sorted(self._skills.values(), key=lambda item: item.name)
        )
