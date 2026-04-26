import pytest
from app.schemas.structured_response import (
    TextResponse, OptionsResponse, PanelResponse, Option, StructuredContent
)

def test_text_response():
    r = TextResponse(content="hello")
    assert r.type == "text"
    assert r.content == "hello"

def test_options_response():
    r = OptionsResponse(
        content="选择数据源类型",
        options=[
            Option(label="Excel/CSV 文件", value="excel"),
            Option(label="数据库", value="database"),
        ]
    )
    assert r.type == "options"
    assert len(r.options) == 2
    assert r.options[0].value == "excel"

def test_panel_response():
    r = PanelResponse(
        content="数据质量报告",
        panel_type="quality_report",
        data={"score": 67, "issues": []}
    )
    assert r.type == "panel"
    assert r.panel_type == "quality_report"
    assert r.data["score"] == 67

def test_structured_content_list():
    items = [
        TextResponse(content="分析完成"),
        PanelResponse(content="结果", panel_type="quality_report", data={"score": 94}),
    ]
    sc = StructuredContent(items=items)
    assert len(sc.items) == 2
    assert sc.items[0].type == "text"
    assert sc.items[1].type == "panel"
