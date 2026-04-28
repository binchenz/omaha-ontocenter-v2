from __future__ import annotations

from typing import Optional

from app.services.agent.skills.loader import Skill, SkillLoader

_STAGE_MAP: dict[str, str] = {
    "idle": "onboarding",
    "connecting": "data_ingestion",
    "cleaning": "data_ingestion",
    "modeling": "data_modeling",
    "ready": "data_query",
}

class SkillResolver:
    def __init__(self, loader: SkillLoader):
        self._loader = loader

    def resolve(self, setup_stage: Optional[str], user_message: str) -> Skill:
        skill_name = _STAGE_MAP.get(setup_stage or "idle", "onboarding")

        # In ready stage, check if any skill's keywords match the message
        if skill_name == "data_query":
            for skill in self._loader.load_all():
                if skill.name == "data_query":
                    continue
                for kw in skill.trigger_keywords:
                    if kw in user_message:
                        skill_name = skill.name
                        break
                else:
                    continue
                break

        skill = self._loader.load(skill_name)
        if skill is None:
            skill = self._loader.load("onboarding")
        return skill
