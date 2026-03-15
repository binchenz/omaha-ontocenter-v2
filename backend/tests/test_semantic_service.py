import pytest
from app.services.semantic import SemanticService

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
          semantic_type: currency
          currency: CNY
          description: "商品售价"
        - name: cost
          column: cost_price
          type: decimal
          description: "商品成本"
        - name: sales_count
          column: qty_sold
          type: integer
          description: "销量"
        - name: status
          column: prd_status
          type: string
          semantic_type: enum
          description: "商品状态"
          enum_values:
            - value: "1"
              label: "在售"
            - value: "0"
              label: "下架"
        - name: gross_margin
          semantic_type: computed
          formula: "(price - cost) / price"
          return_type: percentage
          description: "商品毛利率"
          business_context: "毛利率 > 30% 视为健康"
        - name: is_high_value
          semantic_type: computed
          formula: "IF(price > 1000 AND sales_count > 100, true, false)"
          return_type: boolean
          description: "高价值商品"
"""


def test_parse_semantic_config():
    svc = SemanticService()
    result = svc.parse_config(SAMPLE_CONFIG)
    assert result["valid"] is True
    obj = result["objects"]["Product"]
    assert "gross_margin" in obj["computed_properties"]
    assert "price" in obj["base_properties"]
    assert obj["property_map"]["price"] == "sale_price"
    assert obj["property_map"]["cost"] == "cost_price"


def test_expand_computed_property_simple():
    svc = SemanticService()
    result = svc.parse_config(SAMPLE_CONFIG)
    obj = result["objects"]["Product"]
    sql = svc.expand_formula("(price - cost) / price", obj["property_map"])
    assert sql == "(sale_price - cost_price) / sale_price"


def test_expand_computed_property_if():
    svc = SemanticService()
    result = svc.parse_config(SAMPLE_CONFIG)
    obj = result["objects"]["Product"]
    sql = svc.expand_formula(
        "IF(price > 1000 AND sales_count > 100, true, false)",
        obj["property_map"]
    )
    assert "CASE WHEN" in sql
    assert "sale_price > 1000" in sql
    assert "qty_sold > 100" in sql


def test_build_agent_context():
    svc = SemanticService()
    result = svc.parse_config(SAMPLE_CONFIG)
    context = svc.build_agent_context(result["objects"]["Product"])
    assert "gross_margin" in context
    assert "毛利率 > 30% 视为健康" in context
    assert "CNY" in context


def test_invalid_formula_reference():
    svc = SemanticService()
    result = svc.parse_config(SAMPLE_CONFIG)
    obj = result["objects"]["Product"]
    with pytest.raises(ValueError, match="unknown property"):
        svc.expand_formula("(price - nonexistent) / price", obj["property_map"])
