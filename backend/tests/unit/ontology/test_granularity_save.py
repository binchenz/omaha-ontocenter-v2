"""Test saving semantic config with granularity fields."""
import pytest
from app.services.semantic.service import semantic_service


SAMPLE_CONFIG_WITH_GRANULARITY = """
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
      primary_key: sku_id
      description: "商品主数据"
      business_context: "商品是核心业务对象，包含商品的基础属性"
      granularity:
        dimensions: [sku_id, date]
        level: transaction
        description: "商品交易级别数据，按 SKU 和日期聚合"
      properties:
        - name: sku_id
          column: sku_id
          type: string
          description: "商品SKU ID"
        - name: price
          column: sale_price
          type: decimal
          semantic_type: currency
          currency: CNY
          description: "商品售价"
"""


def test_parse_config_with_granularity():
    """Test that parse_config correctly extracts granularity fields."""
    result = semantic_service.parse_config(SAMPLE_CONFIG_WITH_GRANULARITY)

    assert result["valid"] is True
    assert result["error"] is None
    assert "Product" in result["objects"]

    product = result["objects"]["Product"]
    assert product["description"] == "商品主数据"
    assert product["business_context"] == "商品是核心业务对象，包含商品的基础属性"

    # Check granularity fields
    assert product["granularity"] is not None
    granularity = product["granularity"]
    assert granularity["dimensions"] == ["sku_id", "date"]
    assert granularity["level"] == "transaction"
    assert granularity["description"] == "商品交易级别数据，按 SKU 和日期聚合"


def test_parse_config_without_granularity():
    """Test that parse_config works when granularity is not present."""
    config_without_granularity = """
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
      primary_key: sku_id
      properties:
        - name: sku_id
          column: sku_id
          type: string
"""
    result = semantic_service.parse_config(config_without_granularity)

    assert result["valid"] is True
    assert "Product" in result["objects"]
    product = result["objects"]["Product"]
    assert product["granularity"] is None


def test_build_agent_context_with_granularity():
    """Test that build_agent_context includes granularity information."""
    result = semantic_service.parse_config(SAMPLE_CONFIG_WITH_GRANULARITY)
    product = result["objects"]["Product"]

    context = semantic_service.build_agent_context(product)

    # Check that granularity info is included in the context
    assert "数据粒度" in context
    assert "sku_id, date" in context
    assert "transaction" in context
    assert "商品交易级别数据" in context
