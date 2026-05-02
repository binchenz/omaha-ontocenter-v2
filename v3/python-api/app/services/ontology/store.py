import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete as sa_delete
from sqlalchemy.orm import selectinload
from app.models.ontology import Ontology, OntologyObject, OntologyProperty, OntologyLink, OntologyFunction, OntologyStatus
from app.schemas.ontology_config import OntologyConfig
from app.services.ontology.slug import slugify


async def _unique_ontology_slug(db: AsyncSession, tenant_id: str, base: str, exclude_id: str | None = None) -> str:
    candidate = base
    i = 0
    while True:
        q = select(Ontology).where(Ontology.tenant_id == tenant_id, Ontology.slug == candidate)
        if exclude_id:
            q = q.where(Ontology.id != exclude_id)
        result = await db.execute(q.limit(1))
        if result.scalar_one_or_none() is None:
            return candidate
        i += 1
        candidate = f"{base}-{i}"


def _insert_child_rows(db: AsyncSession, ontology_id: str, config: OntologyConfig) -> None:
    """Insert objects, properties, links, and functions for an ontology. Shared by create and rebuild."""
    for obj_def in config.objects:
        obj = OntologyObject(
            id=str(uuid.uuid4())[:8],
            ontology_id=ontology_id,
            name=obj_def.name,
            slug=slugify(obj_def.slug or obj_def.name),
            description=obj_def.description,
            datasource_id=obj_def.datasource_id,
            table_name=obj_def.table_name,
        )
        db.add(obj)
        for prop_def in obj_def.properties:
            db.add(OntologyProperty(
                id=str(uuid.uuid4())[:8],
                object_id=obj.id,
                name=prop_def.name,
                slug=slugify(prop_def.slug or prop_def.name),
                semantic_type=prop_def.semantic_type,
                source_column=prop_def.source_column,
                is_computed=prop_def.is_computed,
                function_ref=prop_def.function_ref,
                unit=prop_def.unit,
            ))

    for link_def in config.links:
        db.add(OntologyLink(
            id=str(uuid.uuid4())[:8],
            ontology_id=ontology_id,
            name=link_def.name,
            from_object=link_def.from_object,
            to_object=link_def.to_object,
            type=link_def.type,
            from_column=link_def.from_column,
            to_column=link_def.to_column,
        ))

    for func_def in config.functions:
        db.add(OntologyFunction(
            id=str(uuid.uuid4())[:8],
            ontology_id=ontology_id,
            name=func_def.name,
            handler=func_def.handler,
            description=func_def.description,
            input_schema=str(func_def.input_schema),
            output_schema=str(func_def.output_schema),
            caching_ttl=func_def.caching_ttl,
        ))


async def _delete_child_rows(db: AsyncSession, ontology_id: str) -> None:
    """Delete all child rows (objects, properties, links, functions) for an ontology.

    Issues one DELETE per child table — properties are pruned via an ID
    subquery so we don't round-trip once per object (was O(N) before).
    """
    obj_id_subq = (
        select(OntologyObject.id)
        .where(OntologyObject.ontology_id == ontology_id)
        .scalar_subquery()
    )
    await db.execute(
        sa_delete(OntologyProperty).where(OntologyProperty.object_id.in_(obj_id_subq))
    )
    await db.execute(sa_delete(OntologyObject).where(OntologyObject.ontology_id == ontology_id))
    await db.execute(sa_delete(OntologyLink).where(OntologyLink.ontology_id == ontology_id))
    await db.execute(sa_delete(OntologyFunction).where(OntologyFunction.ontology_id == ontology_id))


async def create_ontology(db: AsyncSession, tenant_id: str, config: OntologyConfig, yaml_source: str = "") -> Ontology:
    base_slug = slugify(config.slug or config.name)
    unique_slug = await _unique_ontology_slug(db, tenant_id, base_slug)
    ontology = Ontology(
        id=str(uuid.uuid4())[:8],
        tenant_id=tenant_id,
        name=config.name,
        slug=unique_slug,
        description=config.description,
        yaml_source=yaml_source,
    )
    db.add(ontology)
    _insert_child_rows(db, ontology.id, config)
    await db.commit()
    await db.refresh(ontology)
    return ontology


async def get_ontology(db: AsyncSession, ontology_id: str, tenant_id: str | None = None) -> Ontology | None:
    query = select(Ontology).where(Ontology.id == ontology_id)
    if tenant_id is not None:
        query = query.where(Ontology.tenant_id == tenant_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_ontology_objects(db: AsyncSession, ontology_id: str) -> list[OntologyObject]:
    result = await db.execute(select(OntologyObject).where(OntologyObject.ontology_id == ontology_id))
    return list(result.scalars().all())


async def get_object_properties(db: AsyncSession, object_id: str) -> list[OntologyProperty]:
    result = await db.execute(select(OntologyProperty).where(OntologyProperty.object_id == object_id))
    return list(result.scalars().all())


async def get_ontology_links(db: AsyncSession, ontology_id: str) -> list[OntologyLink]:
    result = await db.execute(select(OntologyLink).where(OntologyLink.ontology_id == ontology_id))
    return list(result.scalars().all())


async def get_ontology_functions(db: AsyncSession, ontology_id: str) -> list[OntologyFunction]:
    result = await db.execute(select(OntologyFunction).where(OntologyFunction.ontology_id == ontology_id))
    return list(result.scalars().all())


async def list_ontologies(
    db: AsyncSession,
    tenant_id: str,
    limit: int | None = None,
    order: str = "desc",
) -> list[Ontology]:
    order_col = Ontology.updated_at.asc() if order == "asc" else Ontology.updated_at.desc()
    stmt = select(Ontology).where(Ontology.tenant_id == tenant_id).order_by(order_col)
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_ontology_schema_full(
    db: AsyncSession, ontology_id: str, tenant_id: str | None = None
) -> Ontology | None:
    """Single-row fetch of an Ontology with all child collections eager-loaded.

    Mirrors :func:`list_ontology_schemas_bulk` so the API serializer can use
    one path for both single-schema and bulk-schema endpoints. Avoids the
    multi-step assembly (objects → per-object properties → links → functions)
    that the legacy ``get_schema`` route used to do via 1+N+2 queries.
    """
    stmt = (
        select(Ontology)
        .where(Ontology.id == ontology_id)
        .options(
            selectinload(Ontology.objects).selectinload(OntologyObject.properties),
            selectinload(Ontology.links),
            selectinload(Ontology.functions),
        )
    )
    if tenant_id is not None:
        stmt = stmt.where(Ontology.tenant_id == tenant_id)
    result = await db.execute(stmt)
    return result.scalars().unique().one_or_none()


async def list_ontology_schemas_bulk(
    db: AsyncSession,
    tenant_id: str,
    limit: int | None = None,
    order: str = "desc",
) -> list[Ontology]:
    """Return ontologies with objects+properties+links+functions eagerly loaded.

    Uses SQLAlchemy ``selectinload`` so the entire payload is fetched in
    a bounded number of queries (1 for ontologies, 1 per eager-loaded
    relationship collection) instead of N+1 per object/property.

    The frontend calls this via ``GET /ontology/schemas`` and iterates the
    result client-side, so per-call we go from 1 HTTP + O(ontologies*objects)
    SELECTs down to 1 HTTP + O(1) SELECTs.
    """
    order_col = Ontology.updated_at.asc() if order == "asc" else Ontology.updated_at.desc()
    stmt = (
        select(Ontology)
        .where(Ontology.tenant_id == tenant_id)
        .options(
            selectinload(Ontology.objects).selectinload(OntologyObject.properties),
            selectinload(Ontology.links),
            selectinload(Ontology.functions),
        )
        .order_by(order_col)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


async def delete_ontology(db: AsyncSession, ontology_id: str) -> bool:
    from app.services.query.view_registry import safe_view_name, invalidate_view_cache
    from app.services.query.duckdb_service import duckdb_service

    ontology = await get_ontology(db, ontology_id)
    if not ontology:
        return False

    objects = await get_ontology_objects(db, ontology_id)
    for obj in objects:
        if obj.table_name:
            try:
                duckdb_service.drop_view(safe_view_name(ontology.tenant_id, obj.table_name))
            except Exception:
                pass
            # Drop the process-level cache entry too so the next query
            # re-registers instead of trusting the stale cache.
            invalidate_view_cache(ontology.tenant_id, obj.table_name)

    await _delete_child_rows(db, ontology_id)
    result = await db.execute(sa_delete(Ontology).where(Ontology.id == ontology_id))
    await db.commit()
    return result.rowcount > 0


async def rebuild_ontology_in_place(
    db: AsyncSession, ontology: Ontology, config: OntologyConfig, yaml_source: str
) -> Ontology:
    await _delete_child_rows(db, ontology.id)

    ontology.name = config.name
    ontology.slug = await _unique_ontology_slug(
        db, ontology.tenant_id, slugify(config.slug or config.name), exclude_id=ontology.id
    )
    ontology.description = config.description
    ontology.yaml_source = yaml_source
    ontology.version = ontology.version + 1

    _insert_child_rows(db, ontology.id, config)
    await db.commit()
    await db.refresh(ontology)
    return ontology
