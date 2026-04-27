from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Skill:
    name: str
    description: str
    system_prompt: str
    allowed_tools: list[str] = field(default_factory=list)
    trigger_keywords: list[str] = field(default_factory=list)


class SkillLoader:
    def __init__(self, definitions_dir: str | Path | None = None):
        if definitions_dir is None:
            definitions_dir = Path(__file__).parent / "definitions"
        self._dir = Path(definitions_dir)

    def load_all(self) -> list[Skill]:
        skills = []
        for path in sorted(self._dir.glob("*.yaml")):
            skill = self._parse(path)
            if skill:
                skills.append(skill)
        return skills

    def load(self, name: str) -> Skill | None:
        path = self._dir / f"{name}.yaml"
        if not path.exists():
            return None
        return self._parse(path)

    def _parse(self, path: Path) -> Skill | None:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return None
        return Skill(
            name=data["name"],
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            allowed_tools=data.get("allowed_tools") or [],
            trigger_keywords=data.get("trigger_keywords") or [],
        )
