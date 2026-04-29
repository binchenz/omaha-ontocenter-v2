"""Tests for the structured response extraction in ChatService."""
import json
from app.services.agent.runtime.conversation import ConversationRuntime


def test_extract_structured_no_block():
    msg, items = ConversationRuntime.extract_structured("just plain text")
    assert msg == "just plain text"
    assert items is None


def test_extract_structured_single_options_block():
    raw = """你好！\n```structured\n{"type": "options", "content": "选行业？", "options": [{"label": "零售", "value": "retail"}]}\n```\n请选择。"""
    msg, items = ConversationRuntime.extract_structured(raw)
    assert items is not None and len(items) == 1
    assert items[0]["type"] == "options"
    assert "structured" not in msg
    assert "请选择" in msg


def test_extract_structured_panel_block():
    payload = {"type": "panel", "panel_type": "quality_report", "content": "报告", "data": {"score": 80, "issues": []}}
    raw = f"""上传完成。\n```structured\n{json.dumps(payload, ensure_ascii=False)}\n```"""
    msg, items = ConversationRuntime.extract_structured(raw)
    assert items is not None and len(items) == 1
    assert items[0]["panel_type"] == "quality_report"
    assert items[0]["data"]["score"] == 80
    assert "上传完成" in msg


def test_extract_structured_invalid_json_skipped():
    raw = """开头\n```structured\n{not valid json}\n```\n结尾"""
    msg, items = ConversationRuntime.extract_structured(raw)
    assert items is None
    assert "开头" in msg and "结尾" in msg


def test_extract_structured_multiple_blocks():
    raw = """text\n```structured\n{"type": "text", "content": "a"}\n```\nmiddle\n```structured\n{"type": "text", "content": "b"}\n```"""
    msg, items = ConversationRuntime.extract_structured(raw)
    assert items is not None and len(items) == 2
    assert "middle" in msg
