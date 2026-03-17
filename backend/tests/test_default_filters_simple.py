"""
Simple unit tests for default_filters functionality.
Tests query_builder directly without importing other app modules.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import only what we need
from app.services.query_builder import SemanticQueryBuilder
from app.services.semantic import semantic_service


def test_default_filters_loaded():
    """Test that default_filters are loaded from YAML config."""
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
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    # Verify default_filters are loaded
    assert hasattr(builder, 'default_filters'), "Builder should have default_filters attribute"
    assert len(builder.default_filters) == 2, f"Expected 2 default filters, got {len(builder.default_filters)}"
    assert builder.default_filters[0]["field"] == "platform_id"
    assert builder.default_filters[0]["operator"] == "IS NOT NULL"

    print("✅ test_default_filters_loaded passed")


def test_build_where_clause_with_default_filters():
    """Test _build_where_clause method with default_filters."""
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
        - name: city
          column: city
          type: string
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    # Test with no user filters
    where_clause, params = builder._build_where_clause(None, "%s")

    assert where_clause.startswith(" WHERE "), f"Expected WHERE clause, got: {where_clause}"
    assert "platform_id IS NOT NULL" in where_clause
    assert "platform_id !=" in where_clause

    print(f"Generated WHERE clause: {where_clause}")
    print(f"Parameters: {params}")
    print("✅ test_build_where_clause_with_default_filters passed")


def test_build_where_clause_combined():
    """Test _build_where_clause with both default and user filters."""
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

    # Test with user filters
    user_filters = [{"field": "city", "operator": "=", "value": "上海"}]
    where_clause, params = builder._build_where_clause(user_filters, "%s")

    assert "platform_id IS NOT NULL" in where_clause, "Should include default filter"
    assert "city = %s" in where_clause, "Should include user filter"
    assert "上海" in params, "Should include user filter value"
    assert " AND " in where_clause, "Should combine filters with AND"

    print(f"Generated WHERE clause: {where_clause}")
    print(f"Parameters: {params}")
    print("✅ test_build_where_clause_combined passed")


def test_full_query_with_default_filters():
    """Test full query building with default_filters."""
    config_yaml = """
ontology:
  objects:
    - name: CompetitorComparison
      table: dm_ppy_platform_product_info_rel_ymd
      default_filters:
        - field: platform_id
          operator: "IS NOT NULL"
        - field: platform_id
          operator: "!="
          value: ""
      properties:
        - name: sku_name
          column: sku_name
          type: string
        - name: platform_id
          column: platform_id
          type: string
        - name: city
          column: city
          type: string
"""

    builder = SemanticQueryBuilder(config_yaml, "CompetitorComparison")

    # Build full query
    query, params = builder.build(
        selected_columns=["sku_name", "city"],
        filters=None,
        joins=None,
        limit=10,
        db_type="mysql"
    )

    assert "SELECT" in query
    assert "FROM dm_ppy_platform_product_info_rel_ymd" in query
    assert "WHERE" in query
    assert "platform_id IS NOT NULL" in query
    assert "platform_id !=" in query
    assert "LIMIT 10" in query

    print(f"\nGenerated SQL:\n{query}")
    print(f"\nParameters: {params}")
    print("✅ test_full_query_with_default_filters passed")


if __name__ == "__main__":
    print("Running default_filters tests...\n")
    test_default_filters_loaded()
    print()
    test_build_where_clause_with_default_filters()
    print()
    test_build_where_clause_combined()
    print()
    test_full_query_with_default_filters()
    print("\n" + "="*80)
    print("✅ All tests passed!")
