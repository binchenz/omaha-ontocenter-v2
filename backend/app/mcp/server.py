"""MCP Server entry point — uses official Python MCP SDK.

Requires Python >= 3.10 and `mcp` package installed.

Run with:
    OMAHA_API_KEY=omaha_1_xxx python -m app.mcp.server
"""
import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from app.mcp.auth import get_api_key_from_env, resolve_api_key
from app.mcp import tools as t
from app.database import SessionLocal

server = Server("omaha-ontocenter")


def _get_context():
    """Resolve API key at startup and return (project_id, config_yaml)."""
    key = get_api_key_from_env()
    db = SessionLocal()
    try:
        result = resolve_api_key(key, db)
    finally:
        db.close()
    if not result:
        raise ValueError("Invalid or expired OMAHA_API_KEY")
    return result


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_objects",
            description="List all Ontology object types defined in the project config.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_schema",
            description="Get column schema for a given object type.",
            inputSchema={
                "type": "object",
                "properties": {"object_type": {"type": "string"}},
                "required": ["object_type"],
            },
        ),
        types.Tool(
            name="get_relationships",
            description="Get available relationships for a given object type.",
            inputSchema={
                "type": "object",
                "properties": {"object_type": {"type": "string"}},
                "required": ["object_type"],
            },
        ),
        types.Tool(
            name="query_data",
            description="Query rows from an ontology object's underlying datasource.",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_type": {"type": "string"},
                    "selected_columns": {"type": "array", "items": {"type": "string"}},
                    "filters": {"type": "array", "items": {"type": "object"}},
                    "joins": {"type": "array", "items": {"type": "object"}},
                    "limit": {"type": "integer", "default": 100},
                },
                "required": ["object_type"],
            },
        ),
        types.Tool(
            name="save_asset",
            description="Save a dataset asset (named query) to the project.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "base_object": {"type": "string"},
                    "description": {"type": "string"},
                    "selected_columns": {"type": "array", "items": {"type": "string"}},
                    "filters": {"type": "array", "items": {"type": "object"}},
                    "joins": {"type": "array", "items": {"type": "object"}},
                    "row_count": {"type": "integer"},
                },
                "required": ["name", "base_object"],
            },
        ),
        types.Tool(
            name="list_assets",
            description="List all saved dataset assets for the project.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        types.Tool(
            name="get_lineage",
            description="Get data lineage records for a saved asset.",
            inputSchema={
                "type": "object",
                "properties": {"asset_id": {"type": "integer"}},
                "required": ["asset_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    project_id, config_yaml = _get_context()

    db = SessionLocal()
    try:
        if name == "list_objects":
            result = t.list_objects(config_yaml)
        elif name == "get_schema":
            result = t.get_schema(config_yaml, arguments["object_type"])
        elif name == "get_relationships":
            result = t.get_relationships(config_yaml, arguments["object_type"])
        elif name == "query_data":
            result = t.query_data(
                config_yaml=config_yaml,
                object_type=arguments["object_type"],
                selected_columns=arguments.get("selected_columns"),
                filters=arguments.get("filters"),
                joins=arguments.get("joins"),
                limit=arguments.get("limit", 100),
            )
        elif name == "save_asset":
            result = t.save_asset(
                db=db,
                project_id=project_id,
                created_by=0,
                name=arguments["name"],
                base_object=arguments["base_object"],
                description=arguments.get("description", ""),
                selected_columns=arguments.get("selected_columns"),
                filters=arguments.get("filters"),
                joins=arguments.get("joins"),
                row_count=arguments.get("row_count"),
            )
        elif name == "list_assets":
            result = t.list_assets(db=db, project_id=project_id)
        elif name == "get_lineage":
            result = t.get_lineage(db=db, asset_id=arguments["asset_id"])
        else:
            result = {"error": f"Unknown tool: {name}"}
    finally:
        db.close()

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
