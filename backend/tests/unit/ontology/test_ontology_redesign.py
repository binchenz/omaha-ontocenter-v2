"""Test Ontology Redesign Phase 2 - Backend Adaptation."""
import pytest
from app.services.semantic.service import semantic_service
from app.services.query.engine import omaha_service


# Sample config with new ontology design features
SAMPLE_CONFIG = """
datasources:
  - id: test_db
    type: sqlite
    connection:
      database: ":memory:"

ontology:
  objects:
    - name: Product
      description: 商品主数据
      datasource: test_db
      table: products
      primary_key: sku_id
      business_context: |
        商品是核心业务对象，包含商品的基础属性。
        价格、成本、销量等动态数据在其他对象中维护。
      granularity:
        dimensions: [sku_id]
        level: master_data
        description: 商品主数据，一个 SKU 一条记录
      properties:
        - name: sku_id
          column: sku_id
          type: integer
          semantic_type: id
          description: SKU ID
          business_context: 商品唯一标识
        - name: sku_name
          column: sku_name
          type: string
          description: SKU名称

    - name: Category
      description: 商品品类
      datasource: test_db
      query: |
        SELECT DISTINCT
          category_name,
          level
        FROM categories
      primary_key: category_name
      business_context: |
        品类用于商品分类管理，支持两级分类体系。
      properties:
        - name: category_name
          type: string
          description: 品类名称
        - name: level
          type: integer
          description: 品类层级

    - name: ProductPrice
      description: 商品价格
      datasource: test_db
      table: product_prices
      primary_key: [sku_id, city, p_date]
      business_context: |
        记录商品在不同城市、不同日期的售价。
      granularity:
        dimensions: [sku_id, city, p_date]
        level: city_daily
        description: 城市+日期粒度的价格数据
      properties:
        - name: sku_id
          column: sku_id
          type: integer
          semantic_type: id
          description: SKU ID
        - name: city
          column: city
          type: string
          description: 城市
        - name: price
          column: price
          type: decimal
          semantic_type: currency
          currency: CNY
          description: 售价
          business_context: 商品在该城市的正常售价
      computed_properties:
        - name: price_with_tax
          formula: "price * 1.13"
          return_type: currency
          description: 含税价格
          business_context: 价格加上13%增值税

  relationships:
    - name: price_of_product
      description: 价格属于哪个商品
      from_object: ProductPrice
      to_object: Product
      type: many_to_one
      join_condition:
        from_field: sku_id
        to_field: sku_id
"""


def test_parse_config_with_granularity():
    """Test parsing config with granularity field."""
    result = semantic_service.parse_config(SAMPLE_CONFIG)

    assert result["valid"] is True
    assert "Product" in result["objects"]
    assert "ProductPrice" in result["objects"]

    # Check granularity parsing
    product = result["objects"]["Product"]
    assert product["granularity"] is not None
    assert product["granularity"]["level"] == "master_data"
    assert product["granularity"]["dimensions"] == ["sku_id"]

    price = result["objects"]["ProductPrice"]
    assert price["granularity"] is not None
    assert price["granularity"]["level"] == "city_daily"
    assert price["granularity"]["dimensions"] == ["sku_id", "city", "p_date"]


def test_parse_config_with_business_context():
    """Test parsing config with business_context field."""
    result = semantic_service.parse_config(SAMPLE_CONFIG)

    assert result["valid"] is True

    product = result["objects"]["Product"]
    assert product["business_context"] is not None
    assert "核心业务对象" in product["business_context"]

    # Check property-level business context
    assert "sku_id" in product["base_properties"]
    sku_prop = product["base_properties"]["sku_id"]
    assert sku_prop.get("business_context") == "商品唯一标识"


def test_parse_config_with_computed_properties_section():
    """Test parsing computed_properties as separate section."""
    result = semantic_service.parse_config(SAMPLE_CONFIG)

    assert result["valid"] is True

    price = result["objects"]["ProductPrice"]
    assert "price_with_tax" in price["computed_properties"]

    computed = price["computed_properties"]["price_with_tax"]
    assert computed["formula"] == "price * 1.13"
    assert computed["return_type"] == "currency"
    assert computed["business_context"] == "价格加上13%增值税"


def test_build_agent_context_with_granularity():
    """Test building agent context includes granularity info."""
    result = semantic_service.parse_config(SAMPLE_CONFIG)
    product = result["objects"]["Product"]

    context = semantic_service.build_agent_context(product)

    assert "商品主数据" in context
    assert "业务上下文" in context
    assert "数据粒度" in context
    assert "master_data" in context
    assert "sku_id" in context


def test_build_agent_context_with_business_context():
    """Test building agent context includes business context."""
    result = semantic_service.parse_config(SAMPLE_CONFIG)
    price = result["objects"]["ProductPrice"]

    context = semantic_service.build_agent_context(price)

    assert "记录商品在不同城市" in context
    assert "业务上下文" in context
    assert "数据粒度" in context
    assert "city_daily" in context
    assert "业务含义" in context


def test_object_with_query_field():
    """Test that objects with 'query' field are parsed correctly."""
    result = semantic_service.parse_config(SAMPLE_CONFIG)

    assert result["valid"] is True
    assert "Category" in result["objects"]

    category = result["objects"]["Category"]
    assert category["description"] == "商品品类"
    assert category["business_context"] is not None


def test_omaha_build_ontology_with_query_objects():
    """Test that omaha service can build ontology with query-based objects."""
    result = omaha_service.build_ontology(SAMPLE_CONFIG)

    assert result["valid"] is True
    objects = result["ontology"]["objects"]

    # Find Category object
    category = next((o for o in objects if o.get("name") == "Category"), None)
    assert category is not None
    assert category.get("query") is not None
    assert "SELECT DISTINCT" in category["query"]


def test_backward_compatibility():
    """Test that old ontology format still works."""
    old_config = """
datasources:
  - id: test_db
    type: sqlite
    connection:
      database: ":memory:"

ontology:
  objects:
    - name: Product
      description: 商品
      datasource: test_db
      table: products
      properties:
        - name: sku_id
          column: sku_id
          type: integer
          description: SKU ID
        - name: price
          column: price
          type: decimal
          semantic_type: computed
          formula: "base_price * 1.1"
          description: 售价
"""

    result = semantic_service.parse_config(old_config)
    assert result["valid"] is True
    assert "Product" in result["objects"]

    product = result["objects"]["Product"]
    # Old format should still work
    assert "sku_id" in product["base_properties"]
    assert "price" in product["computed_properties"]
