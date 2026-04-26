import pytest
from app.services.legacy.financial.query_builder import SemanticQueryBuilder

SAMPLE_CONFIG = """
datasources:
  - id: test_db
    type: sqlite
    connection:
      database: ./test.db
ontology:
  objects:
    - name: Product
      datasource: test_db
      table: products
      primary_key: id
      properties:
        - name: price
          column: sale_price
          type: decimal
          description: 售价
        - name: cost
          column: cost_price
          type: decimal
          description: 成本
        - name: name
          column: product_name
          type: string
        - name: gross_margin
          semantic_type: computed
          formula: "(price - cost) / price"
          return_type: percentage
          description: 毛利率
"""


def test_resolve_regular_column():
    builder = SemanticQueryBuilder(SAMPLE_CONFIG, "Product")
    result = builder.resolve_column("Product.price")
    assert "sale_price" in result


def test_resolve_computed_column():
    builder = SemanticQueryBuilder(SAMPLE_CONFIG, "Product")
    result = builder.resolve_column("Product.gross_margin")
    assert "sale_price" in result
    assert "cost_price" in result
    assert "gross_margin" in result  # AS alias


def test_build_query_with_computed_column():
    builder = SemanticQueryBuilder(SAMPLE_CONFIG, "Product")
    sql, params = builder.build(
        selected_columns=["Product.name", "Product.gross_margin"],
        filters=None,
        joins=None,
        limit=10,
        db_type="sqlite"
    )
    assert "sale_price" in sql
    assert "cost_price" in sql
    assert "gross_margin" in sql
    assert "LIMIT 10" in sql
    assert params == []


def test_build_query_with_filter_on_computed():
    builder = SemanticQueryBuilder(SAMPLE_CONFIG, "Product")
    sql, params = builder.build(
        selected_columns=["Product.name"],
        filters=[{"field": "gross_margin", "operator": ">", "value": 0.3}],
        joins=None,
        limit=10,
        db_type="sqlite"
    )
    assert "sale_price" in sql
    assert "cost_price" in sql
    assert params == [0.3]


def test_build_query_no_columns():
    builder = SemanticQueryBuilder(SAMPLE_CONFIG, "Product")
    sql, params = builder.build(
        selected_columns=None,
        filters=None,
        joins=None,
        limit=100,
        db_type="sqlite"
    )
    assert "FROM products AS Product" in sql
    assert "LIMIT 100" in sql
