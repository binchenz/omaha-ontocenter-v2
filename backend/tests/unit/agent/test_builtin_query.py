"""Tests for builtin query tools."""
import pytest
from unittest.mock import MagicMock

from app.services.agent.tools.registry import ToolContext, ToolResult, global_registry

# Import to trigger registration
import app.services.agent.tools.builtin.query  # noqa: F401


SAMPLE_OBJECTS = [
    {
        "name": "Stock",
        "description": "A listed stock",
        "properties": [
            {"name": "ts_code", "type": "string"},
            {"name": "close", "type": "float"},
        ],
    },
    {
        "name": "Financial",
        "description": "Financial report",
        "properties": [{"name": "revenue", "type": "float"}],
    },
]

SAMPLE_RELATIONSHIPS = [
    {"name": "stock_financial", "from_object": "Stock", "to_object": "Financial"},
    {"name": "financial_other", "from_object": "Financial", "to_object": "Other"},
]


@pytest.fixture
def ctx():
    mock_svc = MagicMock()
    return ToolContext(
        db=None,
        omaha_service=mock_svc,
        ontology_context={
            "objects": SAMPLE_OBJECTS,
            "relationships": SAMPLE_RELATIONSHIPS,
        },
    )


async def test_query_data(ctx):
    ctx.omaha_service.query_objects.return_value = {"rows": [{"ts_code": "000001.SZ"}]}

    result = await global_registry.execute(
        "query_data",
        {"object_type": "Stock", "limit": 10},
        ctx,
    )

    assert result.success is True
    ctx.omaha_service.query_objects.assert_called_once_with(
        object_type="Stock",
        selected_columns=None,
        filters=None,
        joins=None,
        limit=10,
    )
    assert result.data["rows"][0]["ts_code"] == "000001.SZ"


async def test_list_objects(ctx):
    result = await global_registry.execute("list_objects", {}, ctx)

    assert result.success is True
    assert result.data["objects"] == SAMPLE_OBJECTS


async def test_get_schema_found(ctx):
    result = await global_registry.execute("get_schema", {"object_type": "Stock"}, ctx)

    assert result.success is True
    assert result.data["schema"]["name"] == "Stock"
    assert len(result.data["schema"]["properties"]) == 2


async def test_get_schema_not_found(ctx):
    result = await global_registry.execute("get_schema", {"object_type": "Unknown"}, ctx)

    assert result.success is False
    assert "Unknown" in result.error


async def test_get_relationships(ctx):
    result = await global_registry.execute(
        "get_relationships", {"object_type": "Stock"}, ctx
    )

    assert result.success is True
    rels = result.data["relationships"]
    assert len(rels) == 1
    assert rels[0]["name"] == "stock_financial"
