"""Tests for ObjectTypeToolFactory."""
import pytest
from app.services.agent.tools.factory import ObjectTypeToolFactory


def test_factory_builds_search_and_count_tools():
    """Test that factory generates search_<slug> and count_<slug> for each object."""
    ontology = {
        "objects": [
            {
                "name": "产品",
                "slug": "product",
                "properties": [
                    {"name": "产品名称", "slug": "name", "type": "string"},
                    {"name": "价格", "slug": "price", "type": "number"},
                ],
            },
            {
                "name": "订单",
                "slug": "order",
                "properties": [
                    {"name": "订单号", "slug": "order_id", "type": "string"},
                ],
            },
        ]
    }

    tools = ObjectTypeToolFactory.build(ontology)

    # Should have 2 objects × 2 tools (search + count) = 4 tools
    assert len(tools) == 4

    tool_names = {t.name for t in tools}
    assert tool_names == {"search_product", "count_product", "search_order", "count_order"}


def test_search_tool_has_flat_string_params():
    """Test that search tool params are flat (no nested array+object)."""
    ontology = {
        "objects": [
            {
                "name": "Product",
                "slug": "product",
                "properties": [
                    {"name": "Name", "slug": "name", "type": "string", "description": "Product name"},
                    {"name": "Price", "slug": "price", "type": "number", "description": "Product price"},
                    {"name": "Stock", "slug": "stock", "type": "integer"},
                ],
            }
        ]
    }

    tools = ObjectTypeToolFactory.build(ontology)
    search_tool = next(t for t in tools if t.name == "search_product")

    params = search_tool.parameters
    assert params["type"] == "object"
    assert "properties" in params

    props = params["properties"]

    # Check string property: exact + contains
    assert "name" in props
    assert props["name"]["type"] == "string"
    assert "name_contains" in props
    assert props["name_contains"]["type"] == "string"

    # Check numeric property: exact + min + max
    assert "price" in props
    assert props["price"]["type"] == "number"
    assert "price_min" in props
    assert props["price_min"]["type"] == "number"
    assert "price_max" in props
    assert props["price_max"]["type"] == "number"

    # Check select param (array of enum slugs)
    assert "select" in props
    assert props["select"]["type"] == "array"
    assert props["select"]["items"]["type"] == "string"
    assert set(props["select"]["items"]["enum"]) == {"name", "price", "stock"}

    # Check sort_by param (enum of slugs and slug_desc)
    assert "sort_by" in props
    assert props["sort_by"]["type"] == "string"
    sort_enum = props["sort_by"]["enum"]
    assert "name" in sort_enum
    assert "name_desc" in sort_enum
    assert "price" in sort_enum
    assert "price_desc" in sort_enum

    # Check limit param
    assert "limit" in props
    assert props["limit"]["type"] == "integer"

    # Ensure no nested structures (OpenAI strict-mode compatible)
    for prop_name, prop_schema in props.items():
        if prop_name == "select":
            # select is array, but items should be simple enum
            assert "enum" in prop_schema["items"]
        else:
            # All other params should be simple types
            assert prop_schema["type"] in ("string", "number", "integer", "array")


def test_count_tool_has_no_select_sort_limit():
    """Test that count tool has filter params but no select/sort_by/limit."""
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

    tools = ObjectTypeToolFactory.build(ontology)
    count_tool = next(t for t in tools if t.name == "count_product")

    params = count_tool.parameters
    props = params["properties"]

    # Should have filter params
    assert "name" in props
    assert "name_contains" in props
    assert "price" in props
    assert "price_min" in props
    assert "price_max" in props

    # Should NOT have select/sort_by/limit
    assert "select" not in props
    assert "sort_by" not in props
    assert "limit" not in props


def test_factory_skips_objects_without_slug():
    """Test that factory skips objects without slug."""
    ontology = {
        "objects": [
            {"name": "Product", "slug": "product", "properties": []},
            {"name": "NoSlug", "properties": []},  # Missing slug
        ]
    }

    tools = ObjectTypeToolFactory.build(ontology)

    # Should only have tools for 'product'
    tool_names = {t.name for t in tools}
    assert tool_names == {"search_product", "count_product"}


def test_factory_skips_properties_without_slug():
    """Test that factory skips properties without slug."""
    ontology = {
        "objects": [
            {
                "name": "Product",
                "slug": "product",
                "properties": [
                    {"name": "Name", "slug": "name", "type": "string"},
                    {"name": "NoSlug", "type": "string"},  # Missing slug
                ],
            }
        ]
    }

    tools = ObjectTypeToolFactory.build(ontology)
    search_tool = next(t for t in tools if t.name == "search_product")

    props = search_tool.parameters["properties"]

    # Should only have params for 'name'
    assert "name" in props
    assert "name_contains" in props

    # Should NOT have params for 'NoSlug'
    assert "NoSlug" not in props
    assert "NoSlug_contains" not in props


def test_factory_includes_property_name_in_description():
    """Test that tool param descriptions reference original property name."""
    ontology = {
        "objects": [
            {
                "name": "产品",
                "slug": "product",
                "properties": [
                    {"name": "产品名称", "slug": "name", "type": "string", "description": "The product name"},
                ],
            }
        ]
    }

    tools = ObjectTypeToolFactory.build(ontology)
    search_tool = next(t for t in tools if t.name == "search_product")

    props = search_tool.parameters["properties"]

    # Description should include original property name
    assert "产品名称" in props["name"]["description"]
    assert "产品名称" in props["name_contains"]["description"]

