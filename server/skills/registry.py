from __future__ import annotations

from server.skills.base import Skill


class SkillRegistry:
    def __init__(self) -> None:
        self._items: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._items[skill.name] = skill

    def get(self, name: str) -> Skill:
        if name not in self._items:
            raise KeyError(f"skill not found: {name}")
        return self._items[name]

    def list(self) -> list[str]:
        return sorted(self._items.keys())


skill_registry = SkillRegistry()

