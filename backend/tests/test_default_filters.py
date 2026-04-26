"""
Unit tests for default_filters functionality in SemanticQueryBuilder.
"""
import pytest

from app.services.legacy.financial.query_builder import SemanticQueryBuilder


def test_default_filters_in_where_clause():
    """Test that default_filters are correctly applied to WHERE clause."""

    # Create a minimal YAML config with default_filters
    config_yaml = """
ontology:
  objects:
    - name: TestObject
      table: test_table
      default_filters:
        - field: platform_id
          operator: "IS NOT NULL"
        - field: platform_id
          operator: "!="
          value: ""
      properties:
        - name: platform_id
          column: platform_id
          type: string
        - name: sku_name
          column: sku_name
          type: string
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    # Verify default_filters are loaded
    assert len(builder.default_filters) == 2
    assert builder.default_filters[0]["field"] == "platform_id"
    assert builder.default_filters[0]["operator"] == "IS NOT NULL"
    assert builder.default_filters[1]["field"] == "platform_id"
    assert builder.default_filters[1]["operator"] == "!="

    # Build query without user filters
    query, params = builder.build(
        selected_columns=["sku_name"],
        filters=None,
        joins=None,
        limit=10,
        db_type="mysql"
    )

    # Verify WHERE clause contains default filters
    assert "WHERE" in query
    assert "platform_id IS NOT NULL" in query
    assert "platform_id !=" in query

    print(f"Generated SQL:\n{query}")
    print(f"Parameters: {params}")


def test_default_filters_combined_with_user_filters():
    """Test that default_filters are combined with user filters using AND."""
    from app.services.legacy.financial.query_builder import SemanticQueryBuilder

    config_yaml = """
ontology:
  objects:
    - name: TestObject
      table: test_table
      default_filters:
        - field: platform_id
          operator: "IS NOT NULL"
      properties:
        - name: platform_id
          column: platform_id
          type: string
        - name: city
          column: city
          type: string
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    # Build query with user filters
    query, params = builder.build(
        selected_columns=["city"],
        filters=[{"field": "city", "operator": "=", "value": "上海"}],
        joins=None,
        limit=10,
        db_type="mysql"
    )

    # Verify WHERE clause contains both default and user filters
    assert "WHERE" in query
    assert "platform_id IS NOT NULL" in query
    assert "city = %s" in query
    assert "上海" in params

    print(f"Generated SQL:\n{query}")
    print(f"Parameters: {params}")


def test_no_default_filters():
    """Test that objects without default_filters work correctly."""
    from app.services.legacy.financial.query_builder import SemanticQueryBuilder

    config_yaml = """
ontology:
  objects:
    - name: TestObject
      table: test_table
      properties:
        - name: sku_name
          column: sku_name
          type: string
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    # Verify default_filters is empty
    assert len(builder.default_filters) == 0

    # Build query without filters
    query, params = builder.build(
        selected_columns=["sku_name"],
        filters=None,
        joins=None,
        limit=10,
        db_type="mysql"
    )

    # Verify no WHERE clause
    assert "WHERE" not in query

    print(f"Generated SQL:\n{query}")


def test_default_filters_apply_to_active_query_builder():
    """Test that default filter and user filter both appear in query and params."""
    from app.services.legacy.financial.query_builder import SemanticQueryBuilder

    config_yaml = """
ontology:
  objects:
    - name: TestObject
      table: test_table
      default_filters:
        - field: platform_id
          operator: "IS NOT NULL"
      properties:
        - name: platform_id
          column: platform_id
          type: string
        - name: city
          column: city
          type: string
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    query, params = builder.build(
        selected_columns=["city"],
        filters=[{"field": "city", "operator": "=", "value": "上海"}],
        joins=None,
        limit=10,
        db_type="mysql"
    )

    assert "platform_id IS NOT NULL" in query
    assert "city = %s" in query
    assert "上海" in params


if __name__ == "__main__":
    test_default_filters_in_where_clause()
    print("\n" + "="*80 + "\n")
    test_default_filters_combined_with_user_filters()
    print("\n" + "="*80 + "\n")
    test_no_default_filters()
    print("\n✅ All tests passed!")
