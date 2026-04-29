"""Regression test for ontology_context structure bug.

The bug: view.py and navigate.py used `ctx.ontology_context.get("ontology", {})`
which always returned {} because OntologyStore.get_full_ontology() returns
a flat structure with "objects" at the top level, not nested under "ontology".

This made all derived tools (search_*/count_*/aggregate_*) fail with
"Object with slug 'X' not found" in production.
"""
import asyncio
from unittest.mock import MagicMock

from app.services.agent.tools.registry import ToolContext
from app.services.agent.tools.view import ToolRegistryView
from app.services.agent.tools.registry import ToolRegistry


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
    view = ToolRegistryView(builtin=ToolRegistry(), derived=[])

    result = asyncio.run(view._execute_derived("search_order", {}, ctx))

    assert result.success is True, f"Expected success, got error: {result.error}"
    assert result.meta is not None
    assert result.meta["object_slug"] == "order"
    assert result.meta["object_type"] == "订单"


def test_count_resolves_object_with_flat_ontology_context():
    ctx = _make_ctx({"success": True, "data": [{"id": "O1"}, {"id": "O2"}]})
    view = ToolRegistryView(builtin=ToolRegistry(), derived=[])

    result = asyncio.run(view._execute_derived("count_order", {}, ctx))

    assert result.success is True, f"Expected success, got error: {result.error}"
    assert result.data["count"] == 2
