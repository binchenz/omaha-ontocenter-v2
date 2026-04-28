"""Tests for ExecutorAgent (ReAct loop)."""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.services.agent.orchestrator.executor import AgentResponse, ExecutorAgent
from app.services.agent.providers.base import LLMResponse, ToolCall, TokenUsage
from app.services.agent.runtime.conversation import ConversationRuntime
from app.services.agent.skills.loader import Skill
from app.services.agent.tools.registry import ToolContext, ToolRegistry, ToolResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def skill():
    return Skill(
        name="data_query",
        description="",
        system_prompt="你是分析助手。",
        allowed_tools=["query_data", "list_objects"],
        trigger_keywords=[],
    )


@pytest.fixture
def registry():
    reg = ToolRegistry()

    @reg.register(
        name="query_data",
        description="查询数据",
        parameters={
            "type": "object",
            "properties": {"object_type": {"type": "string"}},
            "required": ["object_type"],
        },
    )
    async def query_data(params, ctx):
        return ToolResult(
            success=True,
            data={"data": [{"ts_code": "000001.SZ"}], "count": 1},
        )

    @reg.register(
        name="list_objects",
        description="列出对象",
        parameters={"type": "object", "properties": {}, "required": []},
    )
    async def list_objects(params, ctx):
        return ToolResult(success=True, data={"objects": []})

    return reg


def _make_runtime(skill: Skill) -> ConversationRuntime:
    rt = ConversationRuntime(skill=skill)
    rt.build_system_prompt({})
    rt.append_user_message("查询股票数据")
    return rt


def _make_ctx() -> ToolContext:
    return ToolContext(db=None, omaha_service=None)


def _text_response(text: str) -> LLMResponse:
    return LLMResponse(content=text, tool_calls=[], usage=TokenUsage())


def _tool_response(name: str, args: dict, call_id: str = "call_1") -> LLMResponse:
    return LLMResponse(
        content=None,
        tool_calls=[ToolCall(id=call_id, name=name, arguments=args)],
        usage=TokenUsage(),
    )


# ---------------------------------------------------------------------------
# Test 1: simple text response (no tool calls)
# ---------------------------------------------------------------------------

async def test_executor_simple_text_response(skill, registry):
    provider = AsyncMock()
    provider.send = AsyncMock(return_value=_text_response("这是直接回答。"))

    agent = ExecutorAgent(provider=provider, registry=registry)
    runtime = _make_runtime(skill)
    ctx = _make_ctx()

    response = await agent.run(runtime, ctx)

    assert isinstance(response, AgentResponse)
    assert response.message == "这是直接回答。"
    assert response.data_table is None
    assert response.tool_calls == []


# ---------------------------------------------------------------------------
# Test 2: tool call then text answer — data_table captured
# ---------------------------------------------------------------------------

async def test_executor_tool_then_answer(skill, registry):
    provider = AsyncMock()
    provider.send = AsyncMock(
        side_effect=[
            _tool_response("query_data", {"object_type": "Stock"}),
            _text_response("找到1只股票：000001.SZ"),
        ]
    )

    agent = ExecutorAgent(provider=provider, registry=registry)
    runtime = _make_runtime(skill)
    ctx = _make_ctx()

    response = await agent.run(runtime, ctx)

    assert response.message == "找到1只股票：000001.SZ"
    assert response.data_table == [{"ts_code": "000001.SZ"}]
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0]["name"] == "query_data"
    assert response.tool_calls[0]["params"] == {"object_type": "Stock"}
    # result_summary should be a non-empty string (truncated to 500 chars)
    assert isinstance(response.tool_calls[0]["result_summary"], str)
    assert len(response.tool_calls[0]["result_summary"]) <= 500


# ---------------------------------------------------------------------------
# Test 3: max_iterations — provider always returns tool calls
# ---------------------------------------------------------------------------

async def test_executor_max_iterations(skill, registry):
    # Provider always returns a tool call, never a text answer
    provider = AsyncMock()
    provider.send = AsyncMock(
        return_value=_tool_response("list_objects", {})
    )

    agent = ExecutorAgent(provider=provider, registry=registry, max_iterations=3)
    runtime = _make_runtime(skill)
    ctx = _make_ctx()

    response = await agent.run(runtime, ctx)

    assert "已达到最大轮次" in response.message
    # provider.send should have been called exactly max_iterations times
    assert provider.send.call_count == 3


# ---------------------------------------------------------------------------
# Test 4: first turn uses 'auto' tool_choice
# ---------------------------------------------------------------------------

async def test_executor_uses_auto_on_first_turn(skill, registry):
    """Verify that ExecutorAgent uses tool_choice='auto' on first turn."""
    provider = AsyncMock()
    provider.send = AsyncMock(return_value=_text_response("直接回答"))

    agent = ExecutorAgent(provider=provider, registry=registry)
    runtime = _make_runtime(skill)
    ctx = _make_ctx()

    await agent.run(runtime, ctx)

    # Check that provider.send was called with tool_choice='auto'
    assert provider.send.call_count == 1
    call_kwargs = provider.send.call_args[1]
    assert call_kwargs.get("tool_choice") == "auto"
