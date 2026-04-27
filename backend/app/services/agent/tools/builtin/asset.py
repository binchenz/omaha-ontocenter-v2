"""Builtin asset tools — save_asset, list_assets, get_lineage (stubs)."""
from __future__ import annotations

from app.services.agent.tools.registry import ToolContext, ToolResult, register_tool


@register_tool(
    "save_asset",
    "将当前数据或分析结果保存为资产。",
    {
        "type": "object",
        "properties": {
            "asset_name": {"type": "string", "description": "资产名称"},
            "asset_type": {"type": "string", "description": "资产类型"},
        },
        "required": ["asset_name"],
    },
)
def save_asset(params: dict, ctx: ToolContext) -> ToolResult:
    asset_name = params.get("asset_name", "")
    return ToolResult(success=True, data={"asset_name": asset_name, "saved": True})


@register_tool(
    "list_assets",
    "列出当前项目的所有资产。",
    {"type": "object", "properties": {}, "required": []},
)
def list_assets(params: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult(success=True, data={"assets": []})


@register_tool(
    "get_lineage",
    "获取指定资产的数据血缘关系。",
    {
        "type": "object",
        "properties": {
            "asset_name": {"type": "string", "description": "资产名称"},
        },
        "required": ["asset_name"],
    },
)
def get_lineage(params: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult(success=True, data={"lineage": []})
