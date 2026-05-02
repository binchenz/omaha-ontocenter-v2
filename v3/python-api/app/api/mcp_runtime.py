"""HTTP-based MCP server endpoint exposing ontology tools as JSON-RPC.

Implements a minimal subset of the MCP protocol over HTTP:
- POST /mcp/{ontology_slug} — JSON-RPC method dispatch
  - tools/list → returns available tools
  - tools/call → invokes a tool with arguments
"""

import json

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api._duckdb_errors import map_duckdb_errors
from app.api.deps import TenantId, get_db
from app.models.ontology import Ontology
from app.services.ontology.dto import collect_ontology_for_tools
from app.services.ontology.store import (
    get_ontology_objects, get_object_properties,
    get_ontology_links,
)
from app.services.mcp.tool_generator import generate_tools
from app.services.query.oag_service import oag_service
from app.services.query.view_registry import ensure_view_registered
from app.services.query.duckdb_service import duckdb_service
from app.services.query.sql_safety import validate_identifier, escape_sql_value
from app.schemas.query import OAGQueryRequest

router = APIRouter(prefix="/mcp", tags=["mcp-runtime"])


async def _resolve_ontology_by_slug(db: AsyncSession, slug: str, tenant_id: str = "default") -> Ontology | None:
    result = await db.execute(
        select(Ontology)
        .where(Ontology.slug == slug, Ontology.tenant_id == tenant_id)
        .order_by(Ontology.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.post("/{ontology_slug}")
async def mcp_dispatch(
    ontology_slug: str, request: dict, tenant_id: TenantId, db: AsyncSession = Depends(get_db)
):
    """JSON-RPC style dispatcher for MCP protocol."""
    ontology = await _resolve_ontology_by_slug(db, ontology_slug, tenant_id)
    if not ontology:
        raise HTTPException(404, f"Ontology '{ontology_slug}' not found")

    method = request.get("method", "")
    params = request.get("params", {})
    rpc_id = request.get("id", 1)

    if method == "tools/list":
        # Shared DTO helper runs the three fetches concurrently.
        obj_dicts, link_dicts, func_dicts = await collect_ontology_for_tools(db, ontology.id)
        tools = generate_tools(ontology.id, obj_dicts, link_dicts, func_dicts)
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": tools}}

    if method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})
        try:
            result = await _execute_tool(db, ontology.id, ontology.tenant_id, tool_name, args)
        except ValueError as e:
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32602, "message": str(e)}}
        # JSON-encode properly so clients see JSON, not Python repr (which uses single quotes).
        text = json.dumps(result, ensure_ascii=False, default=str)
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"content": [{"type": "text", "text": text}]}}

    raise HTTPException(400, f"Unknown method: {method}")


async def _execute_tool(db: AsyncSession, ontology_id: str, tenant_id: str, tool_name: str, args: dict):
    # Special-case tools that don't map to a single object
    if tool_name == "navigate_path":
        return await _execute_navigate(db, ontology_id, tenant_id, args)
    if tool_name == "call_function":
        return await _execute_call_function(db, ontology_id, args)

    operation, object_slug = _parse_tool_name(tool_name)
    if not operation or not object_slug:
        raise ValueError(f"Invalid tool name: {tool_name}")

    objects = await get_ontology_objects(db, ontology_id)
    obj = next((o for o in objects if o.slug == object_slug), None)
    if not obj:
        raise ValueError(f"Object '{object_slug}' not found")
    props = await get_object_properties(db, obj.id)

    view_name = await ensure_view_registered(db, obj.table_name, tenant_id)

    obj_dict = {"name": obj.name, "slug": obj.slug, "table_name": view_name, "delta_path": ""}
    props_list = [{"name": p.name, "semantic_type": p.semantic_type, "source_column": p.source_column, "unit": p.unit} for p in props]

    request = OAGQueryRequest(
        operation=operation,
        object=obj.slug,
        filters=args.get("filters"),
        limit=args.get("limit", 50),
        measures=args.get("measures"),
        group_by=args.get("group_by"),
    )

    with map_duckdb_errors():
        response = await oag_service.execute(request, obj_dict, props_list)
    return response.model_dump()


async def _execute_navigate(db: AsyncSession, ontology_id: str, tenant_id: str, args: dict) -> dict:
    """Execute a multi-hop navigation across object links."""
    from app.services.ontology.store import get_ontology_links

    start_object = args.get("start_object")
    start_id = args.get("start_id")
    path = args.get("path", [])
    if not start_object or not start_id or not path:
        raise ValueError("navigate_path 需要 start_object, start_id, path")

    objects = await get_ontology_objects(db, ontology_id)
    links = await get_ontology_links(db, ontology_id)

    obj_map = {o.slug: o for o in objects}
    steps: list[dict] = []
    current_slug = start_object
    current_id = start_id

    for next_slug in path:
        link = next((l for l in links if l.from_object == current_slug and l.to_object == next_slug), None)
        if not link:
            raise ValueError(f"未找到从 {current_slug} 到 {next_slug} 的链接")
        target_obj = obj_map.get(next_slug)
        if not target_obj:
            raise ValueError(f"对象 {next_slug} 不存在")

        view_name = await ensure_view_registered(db, target_obj.table_name, tenant_id)
        target_col = link.to_column or "id"
        validate_identifier(target_col)
        safe_id = escape_sql_value(current_id)
        sql = f'SELECT * FROM "{view_name}" WHERE "{target_col}" = \'{safe_id}\' LIMIT 10'
        rows = duckdb_service.query(sql)
        if not rows:
            # Partial-path failure: surface the walked steps in the error payload
            # so the caller can see how far we got.
            raise ValueError(
                f"在 {next_slug} 中未找到 id={current_id}; walked {len(steps)} step(s)"
            )

        steps.append({"object": next_slug, "result": rows[0]})
        current_slug = next_slug
        # For the next hop, use the target row's primary key (id) — not the FK column
        # we just matched on. The next link's from_column will reference this object's id.
        current_id = rows[0].get("id") or rows[0].get(target_col, current_id)

    return {"steps": steps, "final": steps[-1] if steps else None}


async def _execute_call_function(db: AsyncSession, ontology_id: str, args: dict) -> dict:
    """Invoke a registered ontology function by name."""
    from sqlalchemy import select
    from app.models.ontology import OntologyFunction
    from app.services.query.function_engine import call_function

    func_name = args.get("function_name")
    kwargs = args.get("kwargs", {})
    if not func_name:
        raise ValueError("call_function 需要 function_name")

    fn_result = await db.execute(
        select(OntologyFunction).where(
            OntologyFunction.ontology_id == ontology_id,
            OntologyFunction.name == func_name,
        )
    )
    fn = fn_result.scalar_one_or_none()
    if not fn:
        raise ValueError(f"函数 {func_name} 未在本体中注册")

    # call_function may raise ValueError itself — let it propagate so the
    # dispatcher converts it to a JSON-RPC error.
    return await call_function(fn.handler, fn.caching_ttl, **kwargs)


def _parse_tool_name(tool_name: str) -> tuple[str, str]:
    """search_order → (search, order); aggregate_product → (aggregate, product)."""
    for prefix in ("search_", "count_", "aggregate_"):
        if tool_name.startswith(prefix):
            return prefix.rstrip("_"), tool_name[len(prefix):]
    return "", ""
