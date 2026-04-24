import pytest
from unittest.mock import MagicMock, patch
from app.services.omaha import OmahaService


GENERAL_CONFIG = """
datasources:
  - id: mysql_erp
    name: ERP Database
    type: sql
    connection:
      url: "sqlite:///:memory:"

ontology:
  objects:
    - name: Order
      datasource: mysql_erp
      source_entity: t_order
      description: Customer purchase order
      properties:
        - name: id
          type: integer
        - name: total_amount
          type: float
          semantic_type: currency_cny
        - name: status
          type: string
          semantic_type: order_status
      default_filters:
        - field: status
          operator: "!="
          value: "deleted"
  relationships: []
"""


def test_parse_config_with_source_entity():
    service = OmahaService(GENERAL_CONFIG)
    result = service.parse_config()
    assert result["valid"] is True


def test_get_object_schema_general():
    service = OmahaService(GENERAL_CONFIG)
    schema = service.get_object_schema("Order")
    assert schema is not None
    assert schema["name"] == "Order"
    field_names = {f["name"] for f in schema["fields"]}
    assert "total_amount" in field_names
    assert "status" in field_names


def test_build_ontology_general():
    service = OmahaService(GENERAL_CONFIG)
    ontology = service.build_ontology()
    assert len(ontology["objects"]) == 1
    assert ontology["objects"][0]["name"] == "Order"


def test_source_entity_backward_compat():
    """api_name should still work as fallback for source_entity."""
    config_with_api_name = """
datasources:
  - id: tushare_pro
    type: tushare
    connection:
      token: test_token
ontology:
  objects:
    - name: Stock
      datasource: tushare_pro
      api_name: stock_basic
      properties:
        - name: ts_code
          type: string
  relationships: []
"""
    service = OmahaService(config_with_api_name)
    schema = service.get_object_schema("Stock")
    assert schema is not None
