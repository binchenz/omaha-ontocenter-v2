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


def test_format_onboarding_ready_is_empty():
    svc = _make_service()
    assert svc._format_onboarding("ready") == ""


def test_format_onboarding_unknown_stage_returns_empty():
    svc = _make_service()
    assert svc._format_onboarding("not-a-real-stage") == ""


def test_build_system_prompt_includes_onboarding():
    svc = _make_service()
    prompt_idle = svc.build_system_prompt(setup_stage="idle")
    prompt_ready = svc.build_system_prompt(setup_stage="ready")
    assert "新用户引导" in prompt_idle
    assert "新用户引导" not in prompt_ready
