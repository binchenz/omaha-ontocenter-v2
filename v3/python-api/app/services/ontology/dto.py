"""Shared DTO helpers for ontology metadata.

These flatten ORM rows to plain dicts that downstream consumers
(`oag_service`, future skill packagers) accept without depending on
SQLAlchemy types. Keeping the projection in one place means call sites
stay short and any new field flows through once.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ontology import OntologyObject, OntologyProperty
from app.services.ontology.store import (
    get_object_properties,
    get_ontology_functions,
    get_ontology_links,
    get_ontology_objects,
)


def serialize_property(p: OntologyProperty) -> dict:
    """Flatten one property row to the shape OAG execute() expects."""
    return {
        "name": p.name,
        "semantic_type": p.semantic_type,
        "source_column": p.source_column,
        "unit": p.unit,
    }


def build_oag_context(
    obj: OntologyObject, view_name: str, properties: list[OntologyProperty],
) -> tuple[dict, list[dict]]:
    """Build the (object_def, properties_def) pair that OAGQueryService.execute
    consumes. `view_name` is the DuckDB view already registered by
    view_registry; delta_path is empty because the view holds the mapping.
    """
    object_def = {
        "name": obj.name,
        "slug": obj.slug,
        "table_name": view_name,
        "delta_path": "",
    }
    properties_def = [serialize_property(p) for p in properties]
    return object_def, properties_def


async def collect_ontology_for_tools(
    db: AsyncSession,
    ontology_id: str,
    *,
    include_properties: bool = False,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Fetch objects, links, and functions for an ontology and flatten to
    dict triples. Three independent DB roundtrips run concurrently via
    ``asyncio.gather``. When ``include_properties`` is True, N additional
    roundtrips (one per object) populate each object's ``properties`` list.
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
                {**serialize_property(p), "slug": p.slug} for p in props
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
