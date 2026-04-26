"""Builtin chart tools registered in the global ToolRegistry."""
from typing import Any

from app.services.agent.chart_engine import ChartEngine
from app.services.agent.tools.registry import ToolContext, ToolResult, register_tool

_engine = ChartEngine()


@register_tool(
    name="generate_chart",
    description="Generate an ECharts chart config from data. Call after query_data to visualize results.",
    parameters={
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Array of data rows",
            },
            "chart_type": {
                "type": "string",
                "description": "Chart type: bar, line, pie, scatter",
            },
            "x_field": {"type": "string", "description": "Field name for X axis / category"},
            "y_field": {"type": "string", "description": "Field name for Y axis / values"},
            "title": {"type": "string", "description": "Chart title"},
        },
        "required": ["data", "chart_type", "x_field", "y_field"],
    },
)
async def generate_chart(params: dict, ctx: ToolContext) -> ToolResult:
    data: list[dict[str, Any]] = params.get("data", [])
    chart_type: str = params.get("chart_type", "bar")
    x_field: str = params.get("x_field", "")
    y_field: str = params.get("y_field", "")
    title: str = params.get("title", "")

    if chart_type == "pie":
        config = {
            "title": {"text": title},
            "tooltip": {"trigger": "item"},
            "series": [{
                "type": "pie",
                "data": [
                    {"name": str(row.get(x_field, "")), "value": row.get(y_field, 0)}
                    for row in data
                ],
            }],
        }
    else:
        config = {
            "title": {"text": title},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": [str(row.get(x_field, "")) for row in data]},
            "yAxis": {"type": "value"},
            "series": [{"type": chart_type, "data": [row.get(y_field, 0) for row in data]}],
        }

    return ToolResult(success=True, data={"chart_config": config})


@register_tool(
    name="auto_chart",
    description="Auto-detect chart type and build ECharts config from data using ChartEngine.",
    parameters={
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Array of data rows",
            },
            "title": {"type": "string", "description": "Optional chart title"},
        },
        "required": ["data"],
    },
)
async def auto_chart(params: dict, ctx: ToolContext) -> ToolResult:
    data: list[dict[str, Any]] = params.get("data", [])
    title: str = params.get("title", "")

    if not data:
        return ToolResult(success=False, error="No data provided")

    chart_type = _engine.select_chart_type(data)
    if chart_type is None:
        return ToolResult(success=True, data={"chart_config": None, "chart_type": None})

    config = _engine.build_chart_config(data, chart_type)
    if config and title:
        config.setdefault("title", {})["text"] = title

    return ToolResult(success=True, data={"chart_config": config, "chart_type": chart_type})
