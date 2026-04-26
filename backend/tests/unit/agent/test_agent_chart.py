from app.services.agent.toolkit import AgentToolkit
from unittest.mock import MagicMock


def test_generate_chart_bar():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    result = toolkit.execute_tool("generate_chart", {
        "data": [
            {"name": "Product A", "sales": 1000},
            {"name": "Product B", "sales": 2000},
            {"name": "Product C", "sales": 1500},
        ],
        "chart_type": "bar",
        "title": "Sales by Product",
        "x_field": "name",
        "y_field": "sales",
    })
    assert result["success"] is True
    config = result["chart_config"]
    assert config["series"][0]["type"] == "bar"
    assert len(config["xAxis"]["data"]) == 3


def test_generate_chart_line():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    result = toolkit.execute_tool("generate_chart", {
        "data": [
            {"month": "Jan", "revenue": 100},
            {"month": "Feb", "revenue": 150},
        ],
        "chart_type": "line",
        "title": "Monthly Revenue",
        "x_field": "month",
        "y_field": "revenue",
    })
    assert result["success"] is True
    assert result["chart_config"]["series"][0]["type"] == "line"


def test_generate_chart_pie():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    result = toolkit.execute_tool("generate_chart", {
        "data": [
            {"category": "A", "value": 30},
            {"category": "B", "value": 70},
        ],
        "chart_type": "pie",
        "title": "Distribution",
        "x_field": "category",
        "y_field": "value",
    })
    assert result["success"] is True
    series = result["chart_config"]["series"][0]
    assert series["type"] == "pie"
    assert len(series["data"]) == 2


def test_generate_chart_empty_data():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    result = toolkit.execute_tool("generate_chart", {
        "data": [],
        "chart_type": "bar",
        "x_field": "name",
        "y_field": "value",
    })
    assert result["success"] is True


def test_tool_definitions_include_chart():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    names = {t["name"] for t in toolkit.get_tool_definitions()}
    assert "generate_chart" in names
