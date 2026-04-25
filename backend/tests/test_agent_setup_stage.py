from unittest.mock import MagicMock
from app.services.agent import AgentService, ONBOARDING_PROMPTS


def _make_service():
    toolkit = MagicMock()
    toolkit.get_tool_definitions.return_value = []
    return AgentService(ontology_context={}, toolkit=toolkit)


def test_format_onboarding_known_stage():
    svc = _make_service()
    assert "新用户引导" in svc._format_onboarding("idle")
    assert "数据清洗" in svc._format_onboarding("cleaning")
    assert "就绪" in svc._format_onboarding("ready")


def test_format_onboarding_unknown_stage_falls_back_to_ready():
    svc = _make_service()
    out = svc._format_onboarding("not-a-real-stage")
    assert out == ONBOARDING_PROMPTS["ready"]


def test_build_system_prompt_includes_onboarding():
    svc = _make_service()
    prompt_idle = svc.build_system_prompt(setup_stage="idle")
    prompt_ready = svc.build_system_prompt(setup_stage="ready")
    assert "新用户引导" in prompt_idle
    assert "新用户引导" not in prompt_ready
