import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
from app.main import app
from app.api.deps import get_current_user

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
        - name: gross_margin
          semantic_type: computed
          formula: "(price - cost) / price"
          return_type: percentage
          description: "商品毛利率"
          business_context: "毛利率 > 30% 视为健康"
"""

mock_user = Mock()
mock_user.id = 1
mock_user.email = "test@test.com"
mock_user.is_active = True


def override_get_current_user():
    return mock_user


@pytest.fixture(autouse=True)
def apply_overrides():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.clear()


client = TestClient(app)


def test_parse_semantic_config_endpoint():
    resp = client.post("/api/v1/semantic/parse", json={"config_yaml": SAMPLE_CONFIG})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert "Product" in data["objects"]
    assert "gross_margin" in data["objects"]["Product"]["computed_properties"]


def test_test_formula_endpoint_success():
    resp = client.post("/api/v1/semantic/test-formula", json={
        "formula": "(price - cost) / price",
        "property_map": {"price": "sale_price", "cost": "cost_price"}
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["sql"] == "(sale_price - cost_price) / sale_price"


def test_test_formula_endpoint_invalid():
    resp = client.post("/api/v1/semantic/test-formula", json={
        "formula": "(price - nonexistent) / price",
        "property_map": {"price": "sale_price"}
    })
    assert resp.status_code == 400
    assert "unknown property" in resp.json()["detail"]


def test_get_schema_with_semantics_endpoint():
    resp = client.post("/api/v1/semantic/schema", json={
        "config_yaml": SAMPLE_CONFIG,
        "object_type": "Product"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["object_type"] == "Product"
    col_names = [c["name"] for c in data["columns"]]
    assert "price" in col_names
    assert "gross_margin" in col_names


def test_parse_config_with_granularity():
    """Test parsing config with granularity and business_context fields."""
    config_with_granularity = """
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
      business_context: "商品是核心业务对象"
      granularity:
        dimensions: [sku_id, date]
        level: transaction
        description: "商品交易级别数据"
      properties:
        - name: sku_id
          column: sku_id
          type: string
          description: "商品SKU ID"
"""
    resp = client.post("/api/v1/semantic/parse", json={"config_yaml": config_with_granularity})
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert "Product" in data["objects"]

    product = data["objects"]["Product"]
    assert product["description"] == "商品主数据"
    assert product["business_context"] == "商品是核心业务对象"
    assert product["granularity"] is not None
    assert product["granularity"]["dimensions"] == ["sku_id", "date"]
    assert product["granularity"]["level"] == "transaction"
    assert product["granularity"]["description"] == "商品交易级别数据"
