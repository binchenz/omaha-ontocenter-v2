"""Derived tools must resolve objects via the flat ontology_context shape
({"objects": [...], "relationships": [...]}) returned by
OntologyStore.get_full_ontology().
"""
import asyncio
from unittest.mock import MagicMock

from app.services.agent.providers.base import ToolSpec
from app.services.agent.tools.registry import ToolContext, ToolRegistry
from app.services.agent.tools.view import ToolRegistryView


_DERIVED_SPECS = [
    ToolSpec(name="search_order", description="Search orders", parameters={}),
    ToolSpec(name="count_order", description="Count orders", parameters={}),
]


def _make_view():
    return ToolRegistryView(builtin=ToolRegistry(), derived=_DERIVED_SPECS)


def _make_ctx(omaha_query_result):
    """Build a ToolContext with the flat ontology_context shape that
    OntologyStore.get_full_ontology() actually returns."""
    omaha_service = MagicMock()
    omaha_service.query_objects.return_value = omaha_query_result
    return ToolContext(
        db=None,
        omaha_service=omaha_service,
        tenant_id=1,
        project_id=1,
        session_id=1,
        ontology_context={
            "objects": [
                {
                    "name": "订单",
                    "slug": "order",
                    "source_entity": "orders",
                    "datasource_id": "rdb",
                    "datasource_type": "sqlite",
                    "properties": [
                        {"name": "id", "slug": "id", "type": "string"},
                        {"name": "amount", "slug": "amount", "type": "number"},
                    ],
                },
            ],
            "relationships": [],
        },
    )


def test_search_resolves_object_with_flat_ontology_context():
    """search_<slug> must find the object using the flat shape from OntologyStore."""
    ctx = _make_ctx({"success": True, "data": [{"id": "O1", "amount": 100}]})

    result = asyncio.run(_make_view().execute("search_order", {}, ctx))

    assert result.success is True, f"Expected success, got error: {result.error}"
    assert result.meta is not None
    assert result.meta["object_slug"] == "order"
    assert result.meta["object_type"] == "订单"


def test_count_resolves_object_with_flat_ontology_context():
    """count_<slug> must find the object using the flat shape from OntologyStore."""
    ctx = _make_ctx({"success": True, "data": [{"id": "O1"}, {"id": "O2"}]})

    result = asyncio.run(_make_view().execute("count_order", {}, ctx))

    assert result.success is True, f"Expected success, got error: {result.error}"
    assert result.data["count"] == 2
