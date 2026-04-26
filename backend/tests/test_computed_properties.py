"""
Unit tests for computed_properties functionality in SemanticQueryBuilder.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.legacy.financial.query_builder import SemanticQueryBuilder


def test_computed_properties_in_select():
    """Test that computed properties are expanded in SELECT clause."""
    config_yaml = """
ontology:
  objects:
    - name: TestObject
      table: test_table
      properties:
        - name: ppy_price
          column: ppy_price
          type: decimal
        - name: mall_price
          column: mall_price
          type: decimal
      computed_properties:
        - name: actual_price_gap
          formula: "ppy_price - mall_price"
          return_type: currency
          description: 实际价差
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    # Verify computed_properties are loaded
    assert "actual_price_gap" in builder.computed_properties
    assert builder.computed_properties["actual_price_gap"]["formula"] == "ppy_price - mall_price"

    # Build query with computed property
    query, params = builder.build(
        selected_columns=["actual_price_gap"],
        filters=None,
        joins=None,
        limit=10,
        db_type="mysql"
    )

    # Verify computed property is expanded to SQL expression
    assert "ppy_price - mall_price" in query
    assert "AS actual_price_gap" in query

    print(f"Generated SQL:\n{query}")
    print("✅ test_computed_properties_in_select passed")


def test_computed_properties_with_base_columns():
    """Test computed properties mixed with base columns."""
    config_yaml = """
ontology:
  objects:
    - name: TestObject
      table: test_table
      properties:
        - name: sku_name
          column: sku_name
          type: string
        - name: ppy_price
          column: ppy_price
          type: decimal
        - name: ppy_current_cost
          column: ppy_current_cost
          type: decimal
      computed_properties:
        - name: gross_margin
          formula: "CASE WHEN ppy_price > 0 THEN (ppy_price - ppy_current_cost) / ppy_price ELSE NULL END"
          return_type: percentage
          description: 毛利率
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    # Build query with both base and computed columns
    query, params = builder.build(
        selected_columns=["sku_name", "gross_margin"],
        filters=None,
        joins=None,
        limit=10,
        db_type="mysql"
    )

    # Verify base column is selected normally
    assert "TestObject.sku_name" in query

    # Verify computed property is expanded
    assert "CASE WHEN" in query
    assert "ppy_price - ppy_current_cost" in query
    assert "AS gross_margin" in query

    print(f"Generated SQL:\n{query}")
    print("✅ test_computed_properties_with_base_columns passed")


def test_computed_properties_in_aggregate():
    """Test computed properties inside aggregate functions."""
    config_yaml = """
ontology:
  objects:
    - name: TestObject
      table: test_table
      properties:
        - name: city
          column: city
          type: string
        - name: ppy_price
          column: ppy_price
          type: decimal
        - name: ppy_current_cost
          column: ppy_current_cost
          type: decimal
      computed_properties:
        - name: gross_margin
          formula: "CASE WHEN ppy_price > 0 THEN (ppy_price - ppy_current_cost) / ppy_price ELSE NULL END"
          return_type: percentage
          description: 毛利率
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    # Build query with aggregate function on computed property
    query, params = builder.build(
        selected_columns=["city", "AVG(gross_margin) as avg_margin"],
        filters=None,
        joins=None,
        limit=10,
        db_type="mysql"
    )

    # Verify computed property is expanded inside AVG()
    assert "AVG(" in query
    assert "CASE WHEN" in query
    assert "ppy_price - ppy_current_cost" in query
    assert "as avg_margin" in query

    # Verify GROUP BY is added
    assert "GROUP BY" in query
    assert "city" in query

    print(f"Generated SQL:\n{query}")
    print("✅ test_computed_properties_in_aggregate passed")


def test_computed_properties_in_filter():
    """Test computed properties in WHERE clause."""
    config_yaml = """
ontology:
  objects:
    - name: TestObject
      table: test_table
      properties:
        - name: ppy_price
          column: ppy_price
          type: decimal
        - name: mall_price
          column: mall_price
          type: decimal
      computed_properties:
        - name: actual_price_gap
          formula: "ppy_price - mall_price"
          return_type: currency
          description: 实际价差
"""

    builder = SemanticQueryBuilder(config_yaml, "TestObject")

    # Build query with filter on computed property
    query, params = builder.build(
        selected_columns=["actual_price_gap"],
        filters=[{"field": "actual_price_gap", "operator": ">", "value": 0}],
        joins=None,
        limit=10,
        db_type="mysql"
    )

    # Verify computed property is expanded in WHERE clause
    assert "WHERE" in query
    assert "(ppy_price - mall_price)" in query
    assert "> %s" in query
    assert 0 in params

    print(f"Generated SQL:\n{query}")
    print(f"Parameters: {params}")
    print("✅ test_computed_properties_in_filter passed")


def test_competitor_comparison_computed_properties():
    """Test CompetitorComparison object with all computed properties."""
    config_yaml = """
ontology:
  objects:
    - name: CompetitorComparison
      table: dm_ppy_platform_product_info_rel_ymd
      default_filters:
        - field: platform_id
          operator: "IS NOT NULL"
      properties:
        - name: sku_name
          column: sku_name
          type: string
        - name: ppy_price
          column: ppy_price
          type: decimal
        - name: mall_price
          column: mall_price
          type: decimal
        - name: ppy_promotion_price
          column: ppy_promotion_price
          type: decimal
        - name: mall_promotion_price
          column: mall_promotion_price
          type: decimal
        - name: price_advantage_flag
          column: price_advantage_flag
          type: integer
      computed_properties:
        - name: effective_ppy_price
          formula: "COALESCE(ppy_promotion_price, ppy_price)"
          return_type: currency
          description: 拼便宜有效售价
        - name: effective_mall_price
          formula: "COALESCE(mall_promotion_price, mall_price)"
          return_type: currency
          description: 竞品有效售价
        - name: actual_price_gap
          formula: "ppy_price - mall_price"
          return_type: currency
          description: 实际价差
        - name: is_price_advantage
          formula: "CASE WHEN price_advantage_flag = 1 THEN 1 ELSE 0 END"
          return_type: boolean
          description: 是否具有价格优势
"""

    builder = SemanticQueryBuilder(config_yaml, "CompetitorComparison")

    # Verify all computed properties are loaded
    assert len(builder.computed_properties) == 4
    assert "effective_ppy_price" in builder.computed_properties
    assert "effective_mall_price" in builder.computed_properties
    assert "actual_price_gap" in builder.computed_properties
    assert "is_price_advantage" in builder.computed_properties

    # Build query with multiple computed properties
    query, params = builder.build(
        selected_columns=["sku_name", "effective_ppy_price", "effective_mall_price", "actual_price_gap"],
        filters=None,
        joins=None,
        limit=10,
        db_type="mysql"
    )

    # Verify all computed properties are expanded
    assert "COALESCE(ppy_promotion_price, ppy_price)" in query
    assert "COALESCE(mall_promotion_price, mall_price)" in query
    assert "ppy_price - mall_price" in query
    assert "AS effective_ppy_price" in query
    assert "AS effective_mall_price" in query
    assert "AS actual_price_gap" in query

    # Verify default filter is applied
    assert "WHERE" in query
    assert "platform_id IS NOT NULL" in query

    print(f"Generated SQL:\n{query}")
    print("✅ test_competitor_comparison_computed_properties passed")


if __name__ == "__main__":
    print("Running computed_properties tests...\n")
    test_computed_properties_in_select()
    print()
    test_computed_properties_with_base_columns()
    print()
    test_computed_properties_in_aggregate()
    print()
    test_computed_properties_in_filter()
    print()
    test_competitor_comparison_computed_properties()
    print("\n" + "="*80)
    print("✅ All tests passed!")
