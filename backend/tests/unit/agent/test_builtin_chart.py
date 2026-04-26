"""Tests for builtin chart tools."""
import pytest
from unittest.mock import MagicMock

from app.services.agent.tools.registry import ToolContext, global_registry

# Import to trigger registration
import app.services.agent.tools.builtin.chart  # noqa: F401


BAR_DATA = [
    {"category": "A", "value": 10},
    {"category": "B", "value": 20},
    {"category": "C", "value": 30},
]

PIE_DATA = [
    {"name": "X", "pct": 40},
    {"name": "Y", "pct": 35},
    {"name": "Z", "pct": 25},
]


@pytest.fixture
def ctx():
    return ToolContext(db=None, omaha_service=MagicMock())


async def test_generate_chart_bar(ctx):
    result = await global_registry.execute(
        "generate_chart",
        {
            "data": BAR_DATA,
            "chart_type": "bar",
            "x_field": "category",
            "y_field": "value",
            "title": "Sales",
        },
        ctx,
    )

    assert result.success is True
    cfg = result.data["chart_config"]
    assert cfg["title"]["text"] == "Sales"
    assert cfg["xAxis"]["data"] == ["A", "B", "C"]
    assert cfg["series"][0]["type"] == "bar"
    assert cfg["series"][0]["data"] == [10, 20, 30]


async def test_generate_chart_pie(ctx):
    result = await global_registry.execute(
        "generate_chart",
        {
            "data": PIE_DATA,
            "chart_type": "pie",
            "x_field": "name",
            "y_field": "pct",
            "title": "Share",
        },
        ctx,
    )

    assert result.success is True
    cfg = result.data["chart_config"]
    assert cfg["series"][0]["type"] == "pie"
    pie_names = [d["name"] for d in cfg["series"][0]["data"]]
    assert pie_names == ["X", "Y", "Z"]
    pie_values = [d["value"] for d in cfg["series"][0]["data"]]
    assert pie_values == [40, 35, 25]


async def test_auto_chart_returns_config(ctx):
    # Categorical + numeric with ≤10 categories → bar
    result = await global_registry.execute(
        "auto_chart",
        {"data": BAR_DATA, "title": "Auto"},
        ctx,
    )

    assert result.success is True
    assert result.data["chart_type"] == "bar"
    assert result.data["chart_config"] is not None
    assert result.data["chart_config"]["series"][0]["type"] == "bar"


async def test_auto_chart_empty_data(ctx):
    result = await global_registry.execute("auto_chart", {"data": []}, ctx)

    assert result.success is False
    assert result.error is not None
