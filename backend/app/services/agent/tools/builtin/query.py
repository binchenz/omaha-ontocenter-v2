"""Builtin query tools registered in the global ToolRegistry."""
from app.services.agent.tools.registry import ToolContext, ToolResult, register_tool


@register_tool(
    name="query_data",
    description="Query data from a business object with optional filters and column selection.",
    parameters={
        "type": "object",
        "properties": {
            "object_type": {"type": "string", "description": "Name of the object to query"},
            "selected_columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Columns to return. Omit for all columns.",
            },
            "filters": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Filter conditions: [{field, operator, value}]",
            },
            "joins": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Join definitions.",
            },
            "limit": {"type": "integer", "description": "Max rows to return (default 100)"},
        },
        "required": ["object_type"],
    },
)
async def query_data(params: dict, ctx: ToolContext) -> ToolResult:
    result = ctx.omaha_service.query_objects(
        object_type=params["object_type"],
        selected_columns=params.get("selected_columns"),
        filters=params.get("filters"),
        joins=params.get("joins"),
        limit=params.get("limit", 100),
    )
    return ToolResult(success=True, data=result)


@register_tool(
    name="list_objects",
    description="List all available business objects and their descriptions.",
    parameters={"type": "object", "properties": {}},
)
async def list_objects(params: dict, ctx: ToolContext) -> ToolResult:
    objects = ctx.ontology_context.get("objects", [])
    return ToolResult(success=True, data={"objects": objects})


@register_tool(
    name="get_schema",
    description="Get the schema (fields, types, semantic types) of a business object.",
    parameters={
        "type": "object",
        "properties": {
            "object_type": {"type": "string", "description": "Name of the object"},
        },
        "required": ["object_type"],
    },
)
async def get_schema(params: dict, ctx: ToolContext) -> ToolResult:
    obj_name = params["object_type"]
    for obj in ctx.ontology_context.get("objects", []):
        if obj["name"] == obj_name:
            return ToolResult(success=True, data={"schema": obj})
    return ToolResult(success=False, error=f"Object '{obj_name}' not found")


@register_tool(
    name="get_relationships",
    description="Get relationships for a given object type from the ontology context.",
    parameters={
        "type": "object",
        "properties": {
            "object_type": {"type": "string", "description": "Name of the object"},
        },
        "required": ["object_type"],
    },
)
async def get_relationships(params: dict, ctx: ToolContext) -> ToolResult:
    obj_name = params["object_type"]
    all_rels = ctx.ontology_context.get("relationships", [])
    rels = [
        r for r in all_rels
        if r.get("from_object") == obj_name or r.get("to_object") == obj_name
    ]
    return ToolResult(success=True, data={"relationships": rels})
