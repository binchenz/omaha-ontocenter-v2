"""Reasoning tools — let the LLM externalize its planning before acting."""
from app.services.agent.tools.registry import ToolContext, ToolResult, register_tool


@register_tool(
    name="think",
    description=(
        "在执行复杂查询前，用这个工具分析问题、制定查询计划。"
        "适用于多对象、多条件、对比、趋势类问题。简单查询可以跳过。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "你的分析和查询计划",
            }
        },
        "required": ["reasoning"],
    },
)
def think(params: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult(success=True, data={"noted": True})
