"""Tests for builtin ingestion tools."""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from app.services.agent.tools.registry import ToolContext, ToolResult
import app.services.agent.tools.builtin.ingestion  # ensure registration


def _ctx(**kwargs) -> ToolContext:
    defaults = dict(db=None, omaha_service=None)
    defaults.update(kwargs)
    return ToolContext(**defaults)


# ---------------------------------------------------------------------------
# assess_quality
# ---------------------------------------------------------------------------

def test_assess_quality_no_data():
    from app.services.agent.tools.registry import global_registry
    ctx = _ctx(uploaded_tables={})
    result = global_registry._handlers["assess_quality"]({}, ctx)
    assert result.success is False
    assert "上传" in result.error


def test_assess_quality_with_data():
    from app.services.agent.tools.registry import global_registry

    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    ctx = _ctx(uploaded_tables={"t": df})

    mock_report = MagicMock()
    mock_report.to_dict.return_value = {"score": 95, "issues": []}

    with patch("app.services.data.cleaner.DataCleaner.assess", return_value=mock_report):
        result = global_registry._handlers["assess_quality"]({}, ctx)

    assert result.success is True
    assert result.data["score"] == 95


# ---------------------------------------------------------------------------
# clean_data
# ---------------------------------------------------------------------------

def test_clean_data_no_data():
    from app.services.agent.tools.registry import global_registry
    ctx = _ctx(uploaded_tables={})
    result = global_registry._handlers["clean_data"]({"rules": []}, ctx)
    assert result.success is False
    assert "上传" in result.error
