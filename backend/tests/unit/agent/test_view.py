"""Tests for ToolRegistryView."""
import pytest
from unittest.mock import Mock, AsyncMock
from app.services.agent.tools.view import ToolRegistryView
from app.services.agent.tools.registry import ToolRegistry, ToolContext, ToolResult
from app.services.agent.providers.base import ToolSpec


@pytest.fixture
def builtin_registry():
    """Create a ToolRegistry with some builtin tools."""
    reg = ToolRegistry()

    @reg.register("query_data", "Query data from ontology", {})
    async def query_data(params, ctx):
        return ToolResult(success=True, data={"builtin": True})

    @reg.register("create_chart", "Create a chart", {})
    async def create_chart(params, ctx):
        return ToolResult(success=True, data={"chart": "created"})

    return reg


@pytest.fixture
def derived_tools():
    """Create some derived per-object tools."""
    return [
        ToolSpec(name="search_product", description="Search products", parameters={}),
        ToolSpec(name="count_product", description="Count products", parameters={}),
        ToolSpec(name="search_order", description="Search orders", parameters={}),
        ToolSpec(name="count_order", description="Count orders", parameters={}),
    ]


@pytest.fixture
def view(builtin_registry, derived_tools):
    """Create a ToolRegistryView."""
    return ToolRegistryView(builtin=builtin_registry, derived=derived_tools)


# ---------------------------------------------------------------------------
# get_specs — wildcard matching
# ---------------------------------------------------------------------------

def test_view_get_specs_all_tools(view):
    """Test get_specs with no whitelist returns all tools."""
    specs = view.get_specs()
    names = {s.name for s in specs}
    assert names == {
        "query_data",
        "create_chart",
        "search_product",
        "count_product",
        "search_order",
        "count_order",
    }


def test_view_matches_wildcard_specs(view):
    """Test wildcard matching for search_* and count_*."""
    # Match all search_* tools
    specs = view.get_specs(whitelist=["search_*"])
    names = {s.name for s in specs}
    assert names == {"search_product", "search_order"}

    # Match all count_* tools
    specs = view.get_specs(whitelist=["count_*"])
    names = {s.name for s in specs}
    assert names == {"count_product", "count_order"}


def test_view_wildcard_matches_builtin_and_derived(builtin_registry, derived_tools):
    """Test wildcard matches both builtin and derived tools."""
    # Add a builtin tool starting with 'search_'
    @builtin_registry.register("search_builtin", "Builtin search", {})
    async def search_builtin(params, ctx):
        return ToolResult(success=True)

    view = ToolRegistryView(builtin=builtin_registry, derived=derived_tools)

    specs = view.get_specs(whitelist=["search_*"])
    names = {s.name for s in specs}
    assert names == {"search_builtin", "search_product", "search_order"}


def test_view_exact_match_builtin(view):
    """Test exact match for builtin tool."""
    specs = view.get_specs(whitelist=["query_data"])
    assert len(specs) == 1
    assert specs[0].name == "query_data"


def test_view_exact_match_derived(view):
    """Test exact match for derived tool."""
    specs = view.get_specs(whitelist=["search_product"])
    assert len(specs) == 1
    assert specs[0].name == "search_product"


def test_view_mixed_whitelist(view):
    """Test whitelist with exact names and wildcards."""
    specs = view.get_specs(whitelist=["query_data", "search_*"])
    names = {s.name for s in specs}
    assert names == {"query_data", "search_product", "search_order"}


def test_view_deduplicates_whitelist(view):
    """Test that duplicate matches are deduplicated."""
    specs = view.get_specs(whitelist=["search_*", "search_product"])
    names = [s.name for s in specs]
    # search_product should appear only once
    assert names.count("search_product") == 1


# ---------------------------------------------------------------------------
# execute — routing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_view_routes_builtin_to_registry(view):
    """Test that builtin tools are routed to builtin.execute."""
    ctx = ToolContext(db=None, omaha_service=None)
    result = await view.execute("query_data", {}, ctx)
    assert result.success is True
    assert result.data["builtin"] is True


@pytest.mark.asyncio
async def test_view_executes_derived_with_omaha(view):
    """Test that derived tools call omaha_service with correct filters."""
    # Mock omaha_service
    omaha_service = Mock()
    omaha_service.query_objects = Mock(
        return_value={"success": True, "data": [{"id": 1}, {"id": 2}]}
    )

    # Mock ontology_context
    ontology = {
        "objects": [
            {
                "name": "产品",
                "slug": "product",
                "properties": [
                    {"name": "产品名称", "slug": "name", "type": "string"},
                    {"name": "价格", "slug": "price", "type": "number"},
                ],
            }
        ]
    }

    ctx = ToolContext(
        db=None,
        omaha_service=omaha_service,
        ontology_context={"ontology": ontology},
    )

    # Execute search_product with filters
    params = {
        "name_contains": "手机",
        "price_min": 100,
        "price_max": 1000,
        "select": ["name", "price"],
        "limit": 10,
    }
    result = await view.execute("search_product", params, ctx)

    assert result.success is True
    assert result.data["success"] is True

    # Verify omaha_service.query_objects was called with correct args
    omaha_service.query_objects.assert_called_once()
    call_kwargs = omaha_service.query_objects.call_args.kwargs

    assert call_kwargs["object_type"] == "产品"
    assert call_kwargs["selected_columns"] == ["name", "price"]
    assert call_kwargs["limit"] == 10

    # Check filters
    filters = call_kwargs["filters"]
    assert len(filters) == 3

    # name_contains → LIKE
    name_filter = next(f for f in filters if f["field"] == "产品名称")
    assert name_filter["operator"] == "LIKE"
    assert name_filter["value"] == "%手机%"

    # price_min → >=
    min_filter = next(f for f in filters if f["operator"] == ">=")
    assert min_filter["field"] == "价格"
    assert min_filter["value"] == 100

    # price_max → <=
    max_filter = next(f for f in filters if f["operator"] == "<=")
    assert max_filter["field"] == "价格"
    assert max_filter["value"] == 1000


@pytest.mark.asyncio
async def test_view_count_tool_returns_count_and_sample(view):
    """Test that count_* tools return count + first 10 rows."""
    omaha_service = Mock()
    # Return 15 rows
    data = [{"id": i} for i in range(15)]
    omaha_service.query_objects = Mock(return_value={"success": True, "data": data})

    ontology = {
        "objects": [
            {
                "name": "Product",
                "slug": "product",
                "properties": [{"name": "ID", "slug": "id", "type": "integer"}],
            }
        ]
    }

    ctx = ToolContext(
        db=None,
        omaha_service=omaha_service,
        ontology_context={"ontology": ontology},
    )

    result = await view.execute("count_product", {}, ctx)

    assert result.success is True
    assert result.data["count"] == 15
    assert len(result.data["data"]) == 10  # Only first 10


@pytest.mark.asyncio
async def test_view_derived_tool_unknown_object_slug(view):
    """Test error when object slug not found in ontology."""
    omaha_service = Mock()
    ontology = {"objects": []}

    ctx = ToolContext(
        db=None,
        omaha_service=omaha_service,
        ontology_context={"ontology": ontology},
    )

    result = await view.execute("search_product", {}, ctx)

    assert result.success is False
    assert "not found" in result.error


@pytest.mark.asyncio
async def test_view_unknown_tool_returns_error(view):
    """Test error when tool name is unknown."""
    ctx = ToolContext(db=None, omaha_service=None)
    result = await view.execute("unknown_tool", {}, ctx)

    assert result.success is False
    assert "Unknown tool" in result.error


@pytest.mark.asyncio
async def test_view_derived_tool_omaha_error_propagates(view):
    """Test that omaha_service errors are propagated."""
    omaha_service = Mock()
    omaha_service.query_objects = Mock(
        return_value={"success": False, "error": "Database connection failed"}
    )

    ontology = {
        "objects": [
            {
                "name": "Product",
                "slug": "product",
                "properties": [{"name": "ID", "slug": "id", "type": "integer"}],
            }
        ]
    }

    ctx = ToolContext(
        db=None,
        omaha_service=omaha_service,
        ontology_context={"ontology": ontology},
    )

    result = await view.execute("search_product", {}, ctx)

    assert result.success is False
    assert "Database connection failed" in result.error


# ---------------------------------------------------------------------------
# _build_filters — suffix parsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_view_build_filters_exact_match(view):
    """Test exact match filter (no suffix)."""
    omaha_service = Mock()
    omaha_service.query_objects = Mock(return_value={"success": True, "data": []})

    ontology = {
        "objects": [
            {
                "name": "Product",
                "slug": "product",
                "properties": [{"name": "Name", "slug": "name", "type": "string"}],
            }
        ]
    }

    ctx = ToolContext(
        db=None,
        omaha_service=omaha_service,
        ontology_context={"ontology": ontology},
    )

    await view.execute("search_product", {"name": "iPhone"}, ctx)

    filters = omaha_service.query_objects.call_args.kwargs["filters"]
    assert len(filters) == 1
    assert filters[0]["field"] == "Name"
    assert filters[0]["operator"] == "="
    assert filters[0]["value"] == "iPhone"


@pytest.mark.asyncio
async def test_view_build_filters_skips_none_values(view):
    """Test that None values are skipped."""
    omaha_service = Mock()
    omaha_service.query_objects = Mock(return_value={"success": True, "data": []})

    ontology = {
        "objects": [
            {
                "name": "Product",
                "slug": "product",
                "properties": [
                    {"name": "Name", "slug": "name", "type": "string"},
                    {"name": "Price", "slug": "price", "type": "number"},
                ],
            }
        ]
    }

    ctx = ToolContext(
        db=None,
        omaha_service=omaha_service,
        ontology_context={"ontology": ontology},
    )

    await view.execute("search_product", {"name": "iPhone", "price": None}, ctx)

    filters = omaha_service.query_objects.call_args.kwargs["filters"]
    # Only name filter should be present
    assert len(filters) == 1
    assert filters[0]["field"] == "Name"


@pytest.mark.asyncio
async def test_view_build_filters_skips_unknown_slugs(view):
    """Test that unknown slugs are skipped."""
    omaha_service = Mock()
    omaha_service.query_objects = Mock(return_value={"success": True, "data": []})

    ontology = {
        "objects": [
            {
                "name": "Product",
                "slug": "product",
                "properties": [{"name": "Name", "slug": "name", "type": "string"}],
            }
        ]
    }

    ctx = ToolContext(
        db=None,
        omaha_service=omaha_service,
        ontology_context={"ontology": ontology},
    )

    await view.execute("search_product", {"name": "iPhone", "unknown_slug": "value"}, ctx)

    filters = omaha_service.query_objects.call_args.kwargs["filters"]
    # Only name filter should be present
    assert len(filters) == 1
    assert filters[0]["field"] == "Name"
