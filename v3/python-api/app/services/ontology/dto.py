"""Shared DTO helpers for ontology metadata.

These flatten ORM rows to plain dicts that downstream consumers
(`mcp.tool_generator.generate_tools`, `oag_service`, skill packagers) accept
without depending on SQLAlchemy types. Keeping the projection in one place
means the call sites stay short and any new field flows through once.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ontology.store import (
    get_object_properties,
    get_ontology_functions,
    get_ontology_links,
    get_ontology_objects,
)


async def collect_ontology_for_tools(
    db: AsyncSession,
    ontology_id: str,
    *,
    include_properties: bool = False,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Fetch objects, links, and functions for an ontology and flatten to
    dict triples consumable by ``generate_tools`` and skill packagers.

    Three independent DB roundtrips are run concurrently via ``asyncio.gather``.
    When ``include_properties`` is True, an additional N roundtrips (one per
    object) populate each object's ``properties`` list — this is opt-in because
    the MCP tool generator itself doesn't read properties; it's only useful for
    callers that go on to execute queries (e.g. the ontology query endpoint,
    which uses its own narrower one-object path).

    The returned dicts are the **union** of fields the existing call sites
    (api/mcp.py and api/mcp_runtime.py tools/list) projected, so consolidating
    here is behavior-preserving for both.
    """
    objects, links, funcs = await asyncio.gather(
        get_ontology_objects(db, ontology_id),
        get_ontology_links(db, ontology_id),
        get_ontology_functions(db, ontology_id),
    )

    obj_dicts: list[dict] = []
    for o in objects:
        entry: dict = {
            "name": o.name,
            "slug": o.slug,
            "description": o.description,
            "table_name": o.table_name,
        }
        if include_properties:
            props = await get_object_properties(db, o.id)
            entry["properties"] = [
                {
                    "name": p.name,
                    "slug": p.slug,
                    "semantic_type": p.semantic_type,
                    "source_column": p.source_column,
                    "unit": p.unit,
                }
                for p in props
            ]
        obj_dicts.append(entry)

    link_dicts = [
        {
            "name": l.name,
            "from_object": l.from_object,
            "to_object": l.to_object,
            "type": l.type,
            "from_column": l.from_column,
            "to_column": l.to_column,
        }
        for l in links
    ]

    func_dicts = [
        {"name": f.name, "handler": f.handler, "description": f.description}
        for f in funcs
    ]

    return obj_dicts, link_dicts, func_dicts
