"""Tests for ConversationRuntime."""
import pytest

from app.services.agent.skills.loader import Skill
from app.services.agent.providers.base import Message, ToolCall
from app.services.agent.runtime.conversation import ConversationRuntime


def _make_skill(system_prompt: str = "专注于财务分析。") -> Skill:
    return Skill(
        name="finance",
        description="Finance skill",
        system_prompt=system_prompt,
        allowed_tools=[],
        trigger_keywords=[],
    )


def _make_runtime(system_prompt: str = "专注于财务分析。") -> ConversationRuntime:
    return ConversationRuntime(skill=_make_skill(system_prompt))


# ---------------------------------------------------------------------------
# build_system_prompt
# ---------------------------------------------------------------------------

def test_build_system_prompt():
    rt = _make_runtime()
    ontology = {
        "objects": [
            {
                "name": "Stock",
                "description": "上市公司股票",
                "properties": [
                    {"name": "ts_code", "type": "string"},
                    {"name": "close", "type": "float", "semantic_type": "currency"},
                ],
            }
        ]
    }
    prompt = rt.build_system_prompt(ontology)

    # Skill prompt injected
    assert "专注于财务分析" in prompt
    # Ontology object present
    assert "Stock" in prompt
    assert "上市公司股票" in prompt
    assert "close" in prompt
    assert "currency" in prompt
    # System message stored as first message
    assert rt.messages[0].role == "system"
    assert rt.messages[0].content == prompt


def test_build_system_prompt_empty_ontology():
    rt = _make_runtime()
    prompt = rt.build_system_prompt({})
    assert "无可用对象" in prompt


# ---------------------------------------------------------------------------
# append_* and get_messages_for_llm
# ---------------------------------------------------------------------------

def test_append_and_get_messages():
    rt = _make_runtime()
    rt.build_system_prompt({})  # adds system message

    rt.append_user_message("你好")
    rt.append_assistant_message("你好，有什么可以帮你？", tool_calls=None)
    rt.append_user_message("查一下苹果的股价")

    msgs = rt.get_messages_for_llm()
    assert len(msgs) == 4
    assert msgs[0].role == "system"
    assert msgs[1].role == "user"
    assert msgs[1].content == "你好"
    assert msgs[2].role == "assistant"
    assert msgs[3].role == "user"
    assert msgs[3].content == "查一下苹果的股价"


def test_append_tool_result():
    rt = _make_runtime()
    rt.append_tool_result(tool_call_id="call_abc123", result='{"data": []}')

    msgs = rt.get_messages_for_llm()
    assert len(msgs) == 1
    msg = msgs[0]
    assert msg.role == "tool"
    assert msg.tool_call_id == "call_abc123"
    assert msg.content == '{"data": []}'


# ---------------------------------------------------------------------------
# extract_structured
# ---------------------------------------------------------------------------

def test_extract_structured():
    raw = (
        "这是分析结果。\n"
        "```structured\n"
        '{"type": "options", "content": "选行业？", "options": [{"label": "零售", "value": "retail"}]}\n'
        "```\n"
        "请选择。"
    )
    cleaned, items = ConversationRuntime.extract_structured(raw)

    assert items is not None
    assert len(items) == 1
    assert items[0]["type"] == "options"
    assert "structured" not in cleaned
    assert "请选择" in cleaned


def test_extract_structured_none():
    cleaned, items = ConversationRuntime.extract_structured("普通文本，没有结构化块。")
    assert items is None
    assert cleaned == "普通文本，没有结构化块。"
