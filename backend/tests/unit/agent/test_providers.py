"""Tests for Provider abstraction layer (base, openai_compat, anthropic)."""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.agent.providers.base import (
    LLMResponse,
    Message,
    ProviderAdapter,
    ToolCall,
    ToolSpec,
    TokenUsage,
)
from app.services.agent.providers.openai_compat import OpenAICompatAdapter
from app.services.agent.providers.anthropic import AnthropicAdapter


# ---------------------------------------------------------------------------
# Dataclass / base tests
# ---------------------------------------------------------------------------

def test_tool_call_creation():
    tc = ToolCall(id="call_1", name="search", arguments={"q": "hello"})
    assert tc.id == "call_1"
    assert tc.name == "search"
    assert tc.arguments == {"q": "hello"}


def test_token_usage_defaults():
    u = TokenUsage()
    assert u.input_tokens == 0
    assert u.output_tokens == 0


def test_llm_response_creation():
    resp = LLMResponse(
        content="hi",
        tool_calls=[],
        usage=TokenUsage(input_tokens=10, output_tokens=5),
    )
    assert resp.content == "hi"
    assert resp.tool_calls == []
    assert resp.usage.input_tokens == 10


def test_provider_adapter_is_abstract():
    with pytest.raises(TypeError):
        ProviderAdapter(model="gpt-4", api_key="key")  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# OpenAICompatAdapter tests
# ---------------------------------------------------------------------------

def _make_openai_text_response(text: str):
    """Build a minimal mock that looks like an openai ChatCompletion."""
    choice = MagicMock()
    choice.message.content = text
    choice.message.tool_calls = None

    usage = MagicMock()
    usage.prompt_tokens = 8
    usage.completion_tokens = 4

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


def _make_openai_tool_response(tool_name: str, tool_args: dict, call_id: str = "call_abc"):
    """Build a mock openai response that contains a tool call."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = tool_name
    tc.function.arguments = json.dumps(tool_args)

    choice = MagicMock()
    choice.message.content = None
    choice.message.tool_calls = [tc]

    usage = MagicMock()
    usage.prompt_tokens = 12
    usage.completion_tokens = 6

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


@pytest.mark.asyncio
async def test_openai_send_no_tools():
    adapter = OpenAICompatAdapter(model="gpt-4o", api_key="sk-test")

    mock_create = AsyncMock(return_value=_make_openai_text_response("Hello!"))

    with patch.object(adapter.client.chat.completions, "create", mock_create):
        result = await adapter.send(
            messages=[Message(role="user", content="Hi")]
        )

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello!"
    assert result.tool_calls == []
    assert result.usage.input_tokens == 8
    assert result.usage.output_tokens == 4


@pytest.mark.asyncio
async def test_openai_send_with_tool_calls():
    adapter = OpenAICompatAdapter(model="gpt-4o", api_key="sk-test")

    mock_resp = _make_openai_tool_response(
        tool_name="get_price",
        tool_args={"ticker": "AAPL"},
        call_id="call_xyz",
    )
    mock_create = AsyncMock(return_value=mock_resp)

    tools = [ToolSpec(name="get_price", description="Get stock price", parameters={"ticker": {"type": "string"}})]

    with patch.object(adapter.client.chat.completions, "create", mock_create):
        result = await adapter.send(
            messages=[Message(role="user", content="What is AAPL price?")],
            tools=tools,
        )

    assert result.content is None
    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.id == "call_xyz"
    assert tc.name == "get_price"
    assert tc.arguments == {"ticker": "AAPL"}


# ---------------------------------------------------------------------------
# AnthropicAdapter tests
# ---------------------------------------------------------------------------

def _make_anthropic_text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text

    usage = MagicMock()
    usage.input_tokens = 10
    usage.output_tokens = 7

    resp = MagicMock()
    resp.content = [block]
    resp.usage = usage
    return resp


def _make_anthropic_tool_response(tool_name: str, tool_input: dict, tool_id: str = "toolu_01"):
    block = MagicMock()
    block.type = "tool_use"
    block.id = tool_id
    block.name = tool_name
    block.input = tool_input

    usage = MagicMock()
    usage.input_tokens = 15
    usage.output_tokens = 9

    resp = MagicMock()
    resp.content = [block]
    resp.usage = usage
    return resp


@pytest.mark.asyncio
async def test_anthropic_send_text_only():
    adapter = AnthropicAdapter(model="claude-3-5-sonnet-20241022", api_key="sk-ant-test")

    mock_create = AsyncMock(return_value=_make_anthropic_text_response("Hello from Claude!"))

    with patch.object(adapter.client.messages, "create", mock_create):
        result = await adapter.send(
            messages=[Message(role="user", content="Hi")]
        )

    assert isinstance(result, LLMResponse)
    assert result.content == "Hello from Claude!"
    assert result.tool_calls == []
    assert result.usage.input_tokens == 10
    assert result.usage.output_tokens == 7


@pytest.mark.asyncio
async def test_anthropic_send_with_tool_use():
    adapter = AnthropicAdapter(model="claude-3-5-sonnet-20241022", api_key="sk-ant-test")

    mock_resp = _make_anthropic_tool_response(
        tool_name="query_stock",
        tool_input={"symbol": "600519"},
        tool_id="toolu_99",
    )
    mock_create = AsyncMock(return_value=mock_resp)

    tools = [ToolSpec(name="query_stock", description="Query stock data", parameters={"symbol": {"type": "string"}})]

    with patch.object(adapter.client.messages, "create", mock_create):
        result = await adapter.send(
            messages=[Message(role="user", content="Show me Moutai data")],
            tools=tools,
        )

    assert result.content is None
    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.id == "toolu_99"
    assert tc.name == "query_stock"
    assert tc.arguments == {"symbol": "600519"}
