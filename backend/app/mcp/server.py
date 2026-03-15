"""MCP Server entry point — raw JSON-RPC 2.0 over stdio.

The official `mcp` SDK requires Python >=3.10; this environment runs 3.9.12,
so we implement the MCP stdio transport directly per the spec.

Run with:
    python -m app.mcp.server
"""
import json
import sys
import os
from typing import Any, Dict, List, Optional

from app.database import SessionLocal
from app.mcp.auth import get_api_key_from_env, resolve_api_key
from app.mcp import tools


# ---------------------------------------------------------------------------
# Tool definitions (returned by tools/list)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "list_objects",
        "description": "List all ontology object types defined in the project config.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_schema",
        "description": "Get column schema for a given object type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_type": {"type": "string", "description": "Ontology object name"},
            },
            "required": ["object_type"],
        },
    },
    {
        "name": "get_relationships",
        "description": "Get available relationships for a given object type.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "object_type": {"type": "string", "description": "Ontology object name"},
            },
            "required": ["object_type"],
        },
    },
    {
        "name": "query_data",
        "description": "Query rows from an ontology object's underlying datasource.",
        "inputSchema": {
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
    },
    {
        "name": "save_asset",
        "description": "Save a dataset asset (named query) to the project.",
        "inputSchema": {
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
    },
    {
        "name": "list_assets",
        "description": "List all saved dataset assets for the project.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_lineage",
        "description": "Get data lineage records for a saved asset.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "asset_id": {"type": "integer"},
            },
            "required": ["asset_id"],
        },
    },
]


# ---------------------------------------------------------------------------
# JSON-RPC helpers
# ---------------------------------------------------------------------------

def _send(obj: Dict[str, Any]) -> None:
    """Write a JSON-RPC message to stdout."""
    line = json.dumps(obj)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def _ok(req_id: Any, result: Any) -> None:
    _send({"jsonrpc": "2.0", "id": req_id, "result": result})


def _err(req_id: Any, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


# ---------------------------------------------------------------------------
# Request handlers
# ---------------------------------------------------------------------------

def _handle_initialize(req_id: Any, _params: Dict[str, Any]) -> None:
    _ok(req_id, {
        "protocolVersion": "2024-11-05",
        "capabilities": {"tools": {}},
        "serverInfo": {"name": "omaha-mcp-server", "version": "1.0.0"},
    })


def _handle_tools_list(req_id: Any) -> None:
    _ok(req_id, {"tools": TOOL_DEFINITIONS})


def _handle_tools_call(
    req_id: Any,
    params: Dict[str, Any],
    project_id: int,
    config_yaml: str,
) -> None:
    name = params.get("name", "")
    args: Dict[str, Any] = params.get("arguments", {})

    try:
        if name == "list_objects":
            result = tools.list_objects(config_yaml)
        elif name == "get_schema":
            result = tools.get_schema(config_yaml, args["object_type"])
        elif name == "get_relationships":
            result = tools.get_relationships(config_yaml, args["object_type"])
        elif name == "query_data":
            result = tools.query_data(
                config_yaml=config_yaml,
                object_type=args["object_type"],
                selected_columns=args.get("selected_columns"),
                filters=args.get("filters"),
                joins=args.get("joins"),
                limit=args.get("limit", 100),
            )
        elif name in ("save_asset", "list_assets", "get_lineage"):
            db = SessionLocal()
            try:
                if name == "save_asset":
                    result = tools.save_asset(
                        db=db,
                        project_id=project_id,
                        created_by=0,  # system/API-key context; no user id available
                        name=args["name"],
                        base_object=args["base_object"],
                        description=args.get("description", ""),
                        selected_columns=args.get("selected_columns"),
                        filters=args.get("filters"),
                        joins=args.get("joins"),
                        row_count=args.get("row_count"),
                    )
                elif name == "list_assets":
                    result = tools.list_assets(db=db, project_id=project_id)
                else:  # get_lineage
                    result = tools.get_lineage(db=db, asset_id=args["asset_id"])
            finally:
                db.close()
        else:
            _err(req_id, -32601, f"Unknown tool: {name}")
            return

        _ok(req_id, {
            "content": [{"type": "text", "text": json.dumps(result)}],
        })
    except KeyError as exc:
        _err(req_id, -32602, f"Missing required argument: {exc}")
    except Exception as exc:
        _err(req_id, -32603, str(exc))


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the MCP stdio server."""
    # Resolve API key once at startup
    api_key = get_api_key_from_env()
    db = SessionLocal()
    try:
        resolved = resolve_api_key(api_key, db)
    finally:
        db.close()

    if resolved is None:
        sys.stderr.write("ERROR: Invalid or expired OMAHA_API_KEY\n")
        sys.exit(1)

    project_id, config_yaml = resolved

    for raw_line in sys.stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue

        try:
            msg = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            _send({"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32700, "message": f"Parse error: {exc}"}})
            continue

        req_id = msg.get("id")
        method = msg.get("method", "")
        params = msg.get("params") or {}

        if method == "initialize":
            _handle_initialize(req_id, params)
        elif method == "notifications/initialized":
            pass  # no response needed
        elif method == "tools/list":
            _handle_tools_list(req_id)
        elif method == "tools/call":
            _handle_tools_call(req_id, params, project_id, config_yaml)
        else:
            if req_id is not None:
                _err(req_id, -32601, f"Method not found: {method}")


if __name__ == "__main__":
    main()
