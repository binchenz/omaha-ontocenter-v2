import pytest
from app.services.agent.skills.loader import Skill, SkillLoader
from app.services.agent.skills.resolver import SkillResolver


@pytest.fixture
def loader():
    return SkillLoader()


@pytest.fixture
def resolver(loader):
    return SkillResolver(loader)


def test_skill_loader_loads_all(loader):
    skills = loader.load_all()
    assert len(skills) == 4
    names = {s.name for s in skills}
    assert names == {"onboarding", "data_ingestion", "data_modeling", "data_query"}


def test_skill_loader_load_by_name(loader):
    skill = loader.load("data_query")
    assert skill is not None
    assert "query_data" in skill.allowed_tools


def test_skill_loader_load_missing(loader):
    assert loader.load("nonexistent") is None


@pytest.mark.parametrize("stage,expected_skill", [
    ("idle", "onboarding"),
    ("connecting", "data_ingestion"),
    ("cleaning", "data_ingestion"),
    ("modeling", "data_modeling"),
    ("ready", "data_query"),
])
def test_skill_resolver_by_stage(resolver, stage, expected_skill):
    skill = resolver.resolve(stage, "hello")
    assert skill.name == expected_skill


def test_skill_resolver_keyword_override(resolver):
    skill = resolver.resolve("ready", "我想修改对象的字段")
    assert skill.name == "data_modeling"
