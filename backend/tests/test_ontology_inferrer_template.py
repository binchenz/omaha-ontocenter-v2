from app.services.ontology_inferrer import (
    compact_template, merge_template_semantic_types,
)
from app.schemas.auto_model import InferredObject, InferredProperty


RETAIL_TEMPLATE = {
    "industry": "retail",
    "objects": [
        {
            "name": "订单",
            "description": "客户的采购订单",
            "properties": [
                {"name": "订单号", "data_type": "string", "semantic_type": "order_id"},
                {"name": "金额", "data_type": "number", "semantic_type": "currency_cny"},
                {"name": "状态", "data_type": "string", "semantic_type": "order_status"},
            ],
        },
    ],
    "relationships": [],
}


def test_compact_template_drops_semantic_types():
    compact = compact_template(RETAIL_TEMPLATE)
    assert compact["objects"][0]["name"] == "订单"
    assert compact["objects"][0]["description"] == "客户的采购订单"
    assert compact["objects"][0]["field_names"] == ["订单号", "金额", "状态"]
    assert "semantic_type" not in str(compact)


def test_merge_template_back_fills_semantic_types():
    inferred = [
        InferredObject(
            name="订单",
            source_entity="orders",
            datasource_id="ds1",
            datasource_type="csv",
            properties=[
                InferredProperty(name="订单号", data_type="string", semantic_type=None),
                InferredProperty(name="金额", data_type="number", semantic_type="text"),
                InferredProperty(name="状态", data_type="string"),
            ],
        ),
    ]
    merged = merge_template_semantic_types(inferred, RETAIL_TEMPLATE)
    props = {p.name: p.semantic_type for p in merged[0].properties}
    assert props["订单号"] == "order_id"
    assert props["金额"] == "currency_cny"
    assert props["状态"] == "order_status"


def test_merge_skips_unknown_objects():
    inferred = [
        InferredObject(
            name="发票",
            source_entity="invoices",
            datasource_id="ds1",
            datasource_type="csv",
            properties=[
                InferredProperty(name="发票号", data_type="string", semantic_type="invoice_id"),
            ],
        ),
    ]
    merged = merge_template_semantic_types(inferred, RETAIL_TEMPLATE)
    assert merged[0].properties[0].semantic_type == "invoice_id"


def test_merge_keeps_inferred_value_when_field_not_in_template():
    inferred = [
        InferredObject(
            name="订单",
            source_entity="orders",
            datasource_id="ds1",
            datasource_type="csv",
            properties=[
                InferredProperty(name="备注", data_type="string", semantic_type="text"),
            ],
        ),
    ]
    merged = merge_template_semantic_types(inferred, RETAIL_TEMPLATE)
    assert merged[0].properties[0].semantic_type == "text"
