import json
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._duckdb_errors import map_duckdb_errors
from app.api.deps import Pagination, TenantId, get_db, pagination
from app.core.locks import ontology_update_lock
from app.schemas.query import OAGQueryRequest
from app.services.ontology.parser import parse_ontology_string
from app.services.ontology.store import (
    create_ontology, get_ontology, get_ontology_objects, get_object_properties,
    get_ontology_links, get_ontology_functions, list_ontologies,
    list_ontology_schemas_bulk, delete_ontology,
    rebuild_ontology_in_place,
)
from app.services.query.oag_service import oag_service
from app.services.query.view_registry import ensure_view_registered

router = APIRouter(prefix="/ontology", tags=["ontology"])


async def _require_ontology(db: AsyncSession, ontology_id: str, tenant_id: str):
    ontology = await get_ontology(db, ontology_id, tenant_id=tenant_id)
    if not ontology:
        raise HTTPException(404, "Ontology not found")
    return ontology


@router.get("")
async def list_all(
    tenant_id: TenantId,
    pg: Annotated[Pagination, Depends(pagination)],
    db: AsyncSession = Depends(get_db),
):
    ontologies = await list_ontologies(db, tenant_id, limit=pg.limit, order=pg.order)
    return [{"id": o.id, "name": o.name, "slug": o.slug, "version": o.version, "status": o.status.value} for o in ontologies]


@router.post("")
async def create(
    tenant_id: TenantId,
    yaml_source: str = "",
    body: dict | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
):
    # Accept yaml_source from query (legacy) or JSON body (preferred for large YAML).
    yaml = yaml_source or (body.get("yaml_source") if body else "")
    if not yaml:
        raise HTTPException(400, "yaml_source is required")
    try:
        config = parse_ontology_string(yaml)
    except Exception as e:
        raise HTTPException(400, f"YAML 解析失败: {e}")
    ontology = await create_ontology(db, tenant_id, config, yaml)
    return {"id": ontology.id, "name": ontology.name, "status": ontology.status.value}


@router.get("/schemas")
async def list_schemas(
    tenant_id: TenantId,
    pg: Annotated[Pagination, Depends(pagination)],
    db: AsyncSession = Depends(get_db),
):
    """Batch variant of ``GET /ontology/{id}/schema`` — returns every ontology
    in the tenant with its objects+properties+links+functions inlined.

    Collapses the N+1 round-trip pattern the chat send-route used to need (one
    GET /ontology plus one GET /ontology/{id}/schema per item) into a single
    HTTP call backed by eager-loaded SQL.

    The shape of each item matches the single-schema endpoint so the frontend
    ``OntologySchema`` type applies unchanged.
    """
    ontologies = await list_ontology_schemas_bulk(
        db, tenant_id, limit=pg.limit, order=pg.order
    )
    return [
        {
            "id": o.id,
            "name": o.name,
            "slug": o.slug,
            "version": o.version,
            "objects": [
                {
                    "id": obj.id,
                    "name": obj.name,
                    "slug": obj.slug,
                    "description": obj.description,
                    "table_name": obj.table_name,
                    "datasource_id": obj.datasource_id,
                    "properties": [
                        {
                            "name": p.name,
                            "slug": p.slug,
                            "semantic_type": p.semantic_type,
                            "source_column": p.source_column,
                            "is_computed": p.is_computed,
                            "function_ref": p.function_ref,
                            "unit": p.unit,
                        }
                        for p in obj.properties
                    ],
                }
                for obj in o.objects
            ],
            "links": [
                {"name": l.name, "from_object": l.from_object, "to_object": l.to_object, "type": l.type}
                for l in o.links
            ],
            "functions": [
                {"name": f.name, "handler": f.handler, "description": f.description}
                for f in o.functions
            ],
        }
        for o in ontologies
    ]


@router.get("/{ontology_id}/schema")
async def get_schema(ontology_id: str, tenant_id: TenantId, db: AsyncSession = Depends(get_db)):
    ontology = await _require_ontology(db, ontology_id, tenant_id)
    objects = await get_ontology_objects(db, ontology_id)
    result_objects = []
    for obj in objects:
        props = await get_object_properties(db, obj.id)
        result_objects.append({
            "id": obj.id,
            "name": obj.name,
            "slug": obj.slug,
            "description": obj.description,
            "table_name": obj.table_name,
            "datasource_id": obj.datasource_id,
            "properties": [{"name": p.name, "slug": p.slug, "semantic_type": p.semantic_type, "source_column": p.source_column, "is_computed": p.is_computed, "function_ref": p.function_ref, "unit": p.unit} for p in props],
        })

    links = await get_ontology_links(db, ontology_id)
    funcs = await get_ontology_functions(db, ontology_id)

    return {
        "id": ontology.id,
        "name": ontology.name,
        "slug": ontology.slug,
        "version": ontology.version,
        "objects": result_objects,
        "links": [{"name": l.name, "from_object": l.from_object, "to_object": l.to_object, "type": l.type} for l in links],
        "functions": [{"name": f.name, "handler": f.handler, "description": f.description} for f in funcs],
    }


@router.post("/{ontology_id}/query")
async def query_ontology(
    ontology_id: str, request: OAGQueryRequest,
    tenant_id: TenantId, db: AsyncSession = Depends(get_db),
):
    ontology = await _require_ontology(db, ontology_id, tenant_id)
    objects = await get_ontology_objects(db, ontology_id)
    obj_def = None
    props = []
    for o in objects:
        if o.slug == request.object or o.name == request.object:
            obj_def = o
            props = await get_object_properties(db, o.id)
            break

    if not obj_def:
        raise HTTPException(404, f"Object '{request.object}' not found in ontology")

    view_name = await ensure_view_registered(db, obj_def.table_name, ontology.tenant_id)

    obj_dict = {
        "name": obj_def.name,
        "slug": obj_def.slug,
        "table_name": view_name,
        "delta_path": "",
    }
    props_list = [{"name": p.name, "semantic_type": p.semantic_type, "source_column": p.source_column, "unit": p.unit} for p in props]

    with map_duckdb_errors():
        return await oag_service.execute(request, obj_dict, props_list)


@router.get("/{ontology_id}/yaml")
async def export_yaml(ontology_id: str, tenant_id: TenantId, db: AsyncSession = Depends(get_db)):
    ontology = await _require_ontology(db, ontology_id, tenant_id)
    return {"yaml": ontology.yaml_source}


@router.put("/{ontology_id}")
async def update(
    ontology_id: str,
    tenant_id: TenantId,
    yaml_source: str = "",
    body: dict | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
):
    yaml = yaml_source or (body.get("yaml_source") if body else "")
    if not yaml:
        raise HTTPException(400, "yaml_source is required")

    async with ontology_update_lock.for_key(ontology_id):
        ontology = await _require_ontology(db, ontology_id, tenant_id)
        try:
            config = parse_ontology_string(yaml)
        except Exception as e:
            raise HTTPException(400, f"YAML 解析失败: {e}")

        try:
            await rebuild_ontology_in_place(db, ontology, config, yaml)
        except Exception as e:
            raise HTTPException(400, f"更新失败，本体已回滚: {e}")

        return {"id": ontology.id, "name": ontology.name, "status": ontology.status.value}


@router.delete("/{ontology_id}")
async def delete(ontology_id: str, tenant_id: TenantId, db: AsyncSession = Depends(get_db)):
    await _require_ontology(db, ontology_id, tenant_id)
    deleted = await delete_ontology(db, ontology_id)
    if not deleted:
        raise HTTPException(404, "Ontology not found")
    return {"deleted": True}


@router.post("/{ontology_id}/function/{func_name}")
async def call_func(
    ontology_id: str, func_name: str,
    tenant_id: TenantId,
    kwargs: str = "{}",
    db: AsyncSession = Depends(get_db),
):
    """Invoke a function registered on this ontology.

    Handler is resolved from OntologyFunction table, NOT from caller-supplied input.
    This prevents arbitrary code execution via the handler parameter.
    """
    from sqlalchemy import select
    from app.models.ontology import OntologyFunction
    from app.services.query.function_engine import call_function

    await _require_ontology(db, ontology_id, tenant_id)

    fn_result = await db.execute(
        select(OntologyFunction).where(
            OntologyFunction.ontology_id == ontology_id,
            OntologyFunction.name == func_name,
        )
    )
    fn = fn_result.scalar_one_or_none()
    if not fn:
        raise HTTPException(404, f"函数 {func_name} 未在本体中注册")

    try:
        parsed_kwargs = json.loads(kwargs)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"kwargs 不是合法的 JSON: {e}")

    try:
        return await call_function(fn.handler, fn.caching_ttl, **parsed_kwargs)
    except (ImportError, AttributeError):
        raise HTTPException(500, f"函数实现未找到: {fn.handler}")
    except TypeError as e:
        raise HTTPException(400, f"函数参数错误: {e}")
