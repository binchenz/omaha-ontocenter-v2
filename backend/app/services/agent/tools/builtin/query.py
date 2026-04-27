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
            "filters_json": {
                "type": "string",
                "description": "Optional JSON array of filters, e.g. '[{\"field\":\"city\",\"operator\":\"=\",\"value\":\"北京\"}]'",
            },
            "joins_json": {
                "type": "string",
                "description": "Optional JSON array of joins, e.g. '[{\"object\":\"Order\",\"on\":\"product_id\"}]'",
            },
            "limit": {"type": "integer", "description": "Max rows to return (default 100)"},
        },
        "required": ["object_type"],
    },
)
async def query_data(params: dict, ctx: ToolContext) -> ToolResult:
    import json
    def _parse(key):
        raw = params.get(key)
        if not raw:
            return None
        if isinstance(raw, list):
            return raw
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None
    result = ctx.omaha_service.query_objects(
        object_type=params["object_type"],
        selected_columns=params.get("selected_columns"),
        filters=_parse("filters_json") or params.get("filters"),
        joins=_parse("joins_json") or params.get("joins"),
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
