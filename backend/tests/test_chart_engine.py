import pytest
from app.services.chart_engine import ChartEngine


def test_select_chart_type_line():
    """Test line chart selection for time series data."""
    engine = ChartEngine()
    data = [
        {"date": "2024-01-01", "value": 100},
        {"date": "2024-01-02", "value": 150},
    ]
    chart_type = engine.select_chart_type(data)
    assert chart_type == "line"


def test_select_chart_type_bar():
    """Test bar chart selection for categorical data."""
    engine = ChartEngine()
    data = [
        {"category": "A", "count": 10},
        {"category": "B", "count": 20},
    ]
    chart_type = engine.select_chart_type(data)
    assert chart_type == "bar"


def test_select_chart_type_none():
    """Test no chart for empty data."""
    engine = ChartEngine()
    data = []
    chart_type = engine.select_chart_type(data)
    assert chart_type is None


def test_build_chart_config_line():
    """Test building line chart config."""
    engine = ChartEngine()
    data = [
        {"date": "2024-01-01", "value": 100},
        {"date": "2024-01-02", "value": 150},
    ]
    config = engine.build_chart_config(data, "line")
    assert config is not None
    assert config["xAxis"]["type"] == "category"
    assert config["yAxis"]["type"] == "value"
    assert len(config["series"]) == 1
    assert config["series"][0]["type"] == "line"
