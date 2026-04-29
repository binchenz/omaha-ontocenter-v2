"""Navigate path tool for multi-hop navigation."""
from app.services.agent.tools.registry import ToolContext, ToolResult, register_tool


@register_tool(
    name="navigate_path",
    description="Navigate through multiple relationships in one call. Follow a path from start object through linked objects.",
    parameters={
        "type": "object",
        "properties": {
            "start_object": {"type": "string", "description": "Starting object slug"},
            "start_filters": {
                "type": "object",
                "description": "Filters for start object (slug-based, e.g. {name: 'value'})",
                "additionalProperties": True,
            },
            "path": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Array of link slugs to follow (e.g. ['category', 'sku'])",
            },
            "path_filters": {
                "type": "array",
                "items": {"type": "object", "additionalProperties": True},
                "description": "Array of filter objects, one per hop (e.g. [{}, {price_min: 1000}])",
            },
            "select": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Fields to return from final object",
            },
            "limit": {"type": "integer", "description": "Max rows to return"},
        },
        "required": ["start_object", "path"],
    },
)
async def navigate_path(params: dict, ctx: ToolContext) -> ToolResult:
    from app.services.agent.link.navigator import PathNavigator

    ontology = ctx.ontology_context

    # Convert path_filters to list if needed
    path_filters = params.get("path_filters", [])
    if isinstance(path_filters, dict):
        path_filters = []

    nav_params = {
        "start_object": params["start_object"],
        "start_filters": params.get("start_filters", {}),
        "path": params["path"],
        "path_filters": path_filters,
        "fields": params.get("select", []),
    }

    result = PathNavigator.navigate(nav_params, ontology, ctx)
    return ToolResult(success=result.get("success", False), data=result.get("data"))
