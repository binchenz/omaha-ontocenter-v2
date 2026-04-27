"""Builtin ingestion tools — upload_file, assess_quality, clean_data."""
from __future__ import annotations

from app.services.agent.tools.registry import ToolContext, ToolResult, register_tool


# ---------------------------------------------------------------------------
# upload_file
# ---------------------------------------------------------------------------

@register_tool(
    "upload_file",
    "用户上传了文件后调用此工具，解析 Excel/CSV 文件并存入平台。",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "上传文件的服务器路径"},
            "table_name": {"type": "string", "description": "存储的表名"},
        },
        "required": ["file_path", "table_name"],
    },
)
def upload_file(params: dict, ctx: ToolContext) -> ToolResult:
    import pandas as pd  # lazy

    file_path = params.get("file_path", "")
    table_name = params.get("table_name", "")
    if not file_path or not table_name:
        return ToolResult(success=False, error="file_path 和 table_name 必填")

    try:
        if file_path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)
        ctx.uploaded_tables[table_name] = df
        return ToolResult(
            success=True,
            data={
                "table_name": table_name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": [{"name": c, "type": str(df[c].dtype)} for c in df.columns],
            },
        )
    except Exception as e:
        return ToolResult(success=False, error=str(e))


# ---------------------------------------------------------------------------
# assess_quality
# ---------------------------------------------------------------------------

@register_tool(
    "assess_quality",
    "评估已上传数据的质量，返回质量评分和问题清单。在用户上传文件后自动调用。",
    {"type": "object", "properties": {}, "required": []},
)
def assess_quality(params: dict, ctx: ToolContext) -> ToolResult:
    from app.services.data.cleaner import DataCleaner  # lazy

    tables = ctx.uploaded_tables
    if not tables:
        return ToolResult(success=False, error="没有已上传的数据，请先上传文件")
    report = DataCleaner.assess(tables)
    return ToolResult(success=True, data=report.to_dict())


# ---------------------------------------------------------------------------
# clean_data
# ---------------------------------------------------------------------------

@register_tool(
    "clean_data",
    "对已上传的数据执行清洗操作。rules 可选值：duplicate_rows, strip_whitespace, standardize_dates",
    {
        "type": "object",
        "properties": {
            "rules": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要执行的清洗规则列表",
            }
        },
        "required": ["rules"],
    },
)
def clean_data(params: dict, ctx: ToolContext) -> ToolResult:
    from app.services.data.cleaner import DataCleaner  # lazy

    tables = ctx.uploaded_tables
    if not tables:
        return ToolResult(success=False, error="没有已上传的数据")
    rules = params.get("rules", [])
    cleaned = DataCleaner.clean(tables, auto_rules=rules)
    summary = {f"{name}_cleaned": len(df) for name, df in cleaned.items()}
    ctx.uploaded_tables.clear()
    ctx.uploaded_tables.update(cleaned)
    return ToolResult(success=True, data=summary)
