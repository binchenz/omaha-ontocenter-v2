import pytest
from unittest.mock import MagicMock
import pandas as pd
from app.services.agent.toolkit import AgentToolkit


@pytest.fixture
def toolkit():
    mock_omaha = MagicMock()
    return AgentToolkit(omaha_service=mock_omaha)


def test_toolkit_has_new_tools(toolkit):
    defs = toolkit.get_tool_definitions()
    names = [d["name"] for d in defs]
    assert "upload_file" in names
    assert "assess_quality" in names
    assert "clean_data" in names


def test_assess_quality_returns_report(toolkit):
    toolkit._uploaded_tables = {
        "orders": pd.DataFrame({"name": ["张三", "张三"], "amount": [100, 100]})
    }
    result = toolkit.execute_tool("assess_quality", {})
    assert result["success"] is True
    assert "score" in result["data"]
    assert "issues" in result["data"]


def test_clean_data_applies_rules(toolkit):
    toolkit._uploaded_tables = {
        "orders": pd.DataFrame({"name": [" 张三 ", "李四  "], "amount": [100, 200]})
    }
    result = toolkit.execute_tool("clean_data", {"rules": ["strip_whitespace", "duplicate_rows"]})
    assert result["success"] is True
    assert result["data"]["orders_cleaned"] == 2


def test_assess_quality_no_data(toolkit):
    # No tables uploaded
    result = toolkit.execute_tool("assess_quality", {})
    assert result["success"] is False
    assert "error" in result
