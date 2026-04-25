import pytest
import json
from unittest.mock import patch, MagicMock
from app.services.ontology_inferrer import OntologyInferrer
from app.services.schema_scanner import TableSummary
from app.schemas.auto_model import (
    TableClassification, InferredObject, InferredRelationship, SEMANTIC_TYPES,
)


MOCK_CLASSIFY_RESPONSE = json.dumps([
    {"name": "t_order", "category": "business", "confidence": 0.95, "description": "Order table"},
    {"name": "t_customer", "category": "business", "confidence": 0.9, "description": "Customer table"},
    {"name": "django_migrations", "category": "system", "confidence": 0.99, "description": "Django framework table"},
])

MOCK_INFER_RESPONSE = json.dumps({
    "name": "订单",
    "source_entity": "t_order",
    "description": "客户采购订单",
    "business_context": "记录客户的购买行为",
    "domain": "retail",
    "properties": [
        {"name": "id", "data_type": "integer", "semantic_type": "id", "description": "订单ID"},
        {"name": "customer_id", "data_type": "integer", "semantic_type": "id", "description": "客户ID"},
        {"name": "total_amount", "data_type": "float", "semantic_type": "currency_cny", "description": "订单金额"},
        {"name": "status", "data_type": "string", "semantic_type": "order_status", "description": "订单状态"},
        {"name": "created_at", "data_type": "datetime", "semantic_type": "datetime", "description": "创建时间"},
    ],
    "suggested_health_rules": [],
    "suggested_computed_properties": [],
})


@pytest.fixture
def inferrer():
    return OntologyInferrer()


@pytest.fixture
def sample_tables():
    return [
        TableSummary(
            name="t_order", row_count=5000,
            columns=[
                {"name": "id", "type": "INTEGER", "nullable": False},
                {"name": "customer_id", "type": "INTEGER", "nullable": True},
                {"name": "total_amount", "type": "REAL", "nullable": True},
                {"name": "status", "type": "TEXT", "nullable": True},
                {"name": "created_at", "type": "TEXT", "nullable": True},
            ],
            sample_values={
                "id": ["1", "2", "3"],
                "customer_id": ["101", "102", "103"],
                "total_amount": ["299.00", "1580.50", "45.00"],
                "status": ["pending", "shipped", "delivered", "cancelled"],
                "created_at": ["2024-01-15", "2024-02-20"],
            },
        ),
        TableSummary(
            name="t_customer", row_count=800,
            columns=[
                {"name": "id", "type": "INTEGER", "nullable": False},
                {"name": "name", "type": "TEXT", "nullable": True},
                {"name": "phone", "type": "TEXT", "nullable": True},
                {"name": "region", "type": "TEXT", "nullable": True},
            ],
            sample_values={
                "id": ["101", "102", "103"],
                "name": ["Alice", "Bob"],
                "phone": ["13800001111", "13900002222"],
                "region": ["East", "West"],
            },
        ),
    ]


def test_parse_json_from_llm_response(inferrer):
    raw = "Here is the result:\n" + MOCK_CLASSIFY_RESPONSE + "\nDone."
    parsed = inferrer._extract_json(raw)
    assert isinstance(parsed, list)
    assert len(parsed) == 3


def test_parse_json_clean_response(inferrer):
    parsed = inferrer._extract_json(MOCK_CLASSIFY_RESPONSE)
    assert isinstance(parsed, list)


def test_parse_json_invalid_returns_none(inferrer):
    parsed = inferrer._extract_json("This is not JSON at all")
    assert parsed is None


@patch.object(OntologyInferrer, "_call_llm")
def test_classify_tables(mock_llm, inferrer, sample_tables):
    mock_llm.return_value = MOCK_CLASSIFY_RESPONSE
    classifications = inferrer.classify_tables(sample_tables)
    assert len(classifications) == 3
    order_cls = next(c for c in classifications if c.name == "t_order")
    assert order_cls.category == "business"


@patch.object(OntologyInferrer, "_call_llm")
def test_infer_table(mock_llm, inferrer, sample_tables):
    mock_llm.return_value = MOCK_INFER_RESPONSE
    result = inferrer.infer_table(sample_tables[0], datasource_id="mysql_erp")
    assert result is not None
    assert result.name == "订单"
    assert result.source_entity == "t_order"
    assert len(result.properties) == 5
    amount_prop = next(p for p in result.properties if p.name == "total_amount")
    assert amount_prop.semantic_type == "currency_cny"


@patch.object(OntologyInferrer, "_call_llm")
def test_infer_table_bad_response_returns_none(mock_llm, inferrer, sample_tables):
    mock_llm.return_value = "I cannot process this request."
    result = inferrer.infer_table(sample_tables[0], datasource_id="mysql_erp")
    assert result is None


def test_infer_relationships_by_naming(inferrer):
    objects = [
        InferredObject(
            name="订单", source_entity="t_order",
            properties=[
                {"name": "id", "data_type": "integer"},
                {"name": "customer_id", "data_type": "integer"},
            ],
        ),
        InferredObject(
            name="客户", source_entity="t_customer",
            properties=[
                {"name": "id", "data_type": "integer"},
                {"name": "name", "data_type": "string"},
            ],
        ),
    ]
    rels = inferrer.infer_relationships_by_naming(objects)
    assert len(rels) == 1
    assert rels[0].from_object == "t_order"
    assert rels[0].to_object == "t_customer"
    assert rels[0].from_field == "customer_id"


def test_semantic_type_validation(inferrer):
    bad_response = json.dumps({
        "name": "Test", "source_entity": "t_test", "description": "test",
        "properties": [
            {"name": "price", "data_type": "float", "semantic_type": "money_amount"},
        ],
    })
    parsed = inferrer._extract_json(bad_response)
    obj = InferredObject.model_validate(parsed)
    cleaned = inferrer._validate_semantic_types(obj)
    assert cleaned.properties[0].semantic_type is None
