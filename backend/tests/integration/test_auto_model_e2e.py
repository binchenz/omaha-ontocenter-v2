"""
End-to-end: create SQLite tables -> scan -> mock LLM infer -> confirm -> verify ontology in DB.
"""
import json
import pytest
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.tenant import Tenant
from app.services.schema_scanner import SchemaScanner
from app.services.ontology_inferrer import OntologyInferrer
from app.services.ontology_importer import OntologyImporter
from app.services.ontology_store import OntologyStore


@pytest.fixture
def setup():
    import tempfile, os
    fd, biz_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    tenant = Tenant(name="E2E Corp", plan="free")
    db.add(tenant)
    db.commit()

    biz_engine = create_engine(f"sqlite:///{biz_path}")
    with biz_engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE t_order (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                total_amount REAL,
                status TEXT
            )
        """))
        conn.execute(text("INSERT INTO t_order VALUES (1, 101, 500.0, 'pending')"))
        conn.execute(text("""
            CREATE TABLE t_customer (
                id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT
            )
        """))
        conn.execute(text("INSERT INTO t_customer VALUES (101, 'Alice', '13800001111')"))
        conn.commit()

    yield db, tenant, biz_engine.url
    db.close()
    os.unlink(biz_path)


MOCK_ORDER_INFER = json.dumps({
    "name": "订单", "source_entity": "t_order",
    "description": "客户订单", "business_context": "购买记录", "domain": "retail",
    "properties": [
        {"name": "id", "data_type": "integer", "semantic_type": "id"},
        {"name": "customer_id", "data_type": "integer", "semantic_type": "id"},
        {"name": "total_amount", "data_type": "float", "semantic_type": "currency_cny"},
        {"name": "status", "data_type": "string", "semantic_type": "order_status"},
    ],
})

MOCK_CUSTOMER_INFER = json.dumps({
    "name": "客户", "source_entity": "t_customer",
    "description": "客户信息", "business_context": "客户档案", "domain": "retail",
    "properties": [
        {"name": "id", "data_type": "integer", "semantic_type": "id"},
        {"name": "name", "data_type": "string", "semantic_type": "text"},
        {"name": "phone", "data_type": "string", "semantic_type": "phone"},
    ],
})


def test_full_auto_model_flow(setup):
    db, tenant, biz_url = setup

    # Step 1: Scan
    scanner = SchemaScanner(str(biz_url))
    summaries = scanner.scan_all()
    assert len(summaries) == 2
    table_names = {s.name for s in summaries}
    assert table_names == {"t_order", "t_customer"}
    scanner.close()

    # Step 2: Infer (mock LLM)
    inferrer = OntologyInferrer()
    infer_responses = {"t_order": MOCK_ORDER_INFER, "t_customer": MOCK_CUSTOMER_INFER}

    objects = []
    with patch.object(OntologyInferrer, "_call_llm") as mock_llm:
        for summary in summaries:
            mock_llm.return_value = infer_responses[summary.name]
            result = inferrer.infer_table(summary, datasource_id="biz_db")
            assert result is not None
            objects.append(result)

    assert len(objects) == 2

    # Step 3: FK matching
    relationships = inferrer.infer_relationships_by_naming(objects)
    assert len(relationships) == 1
    assert relationships[0].from_field == "customer_id"

    # Step 4: Confirm (write to DB)
    importer = OntologyImporter(db)
    config = {
        "datasources": [{"id": "biz_db", "type": "sql"}],
        "ontology": {
            "objects": [
                {
                    "name": obj.name,
                    "datasource": obj.datasource_id,
                    "source_entity": obj.source_entity,
                    "description": obj.description,
                    "domain": obj.domain,
                    "properties": [
                        {"name": p.name, "type": p.data_type, "semantic_type": p.semantic_type}
                        for p in obj.properties
                    ],
                }
                for obj in objects
            ],
            "relationships": [
                {
                    "name": r.name, "from_object": r.from_object, "to_object": r.to_object,
                    "type": r.relationship_type, "from_field": r.from_field, "to_field": r.to_field,
                }
                for r in relationships
            ],
        },
    }
    result = importer.import_dict(tenant_id=tenant.id, config=config)
    assert result["objects_created"] == 2
    assert result["relationships_created"] == 1

    # Step 5: Verify in DB
    store = OntologyStore(db)
    ontology = store.get_full_ontology(tenant.id)
    assert len(ontology["objects"]) == 2
    assert len(ontology["relationships"]) == 1

    order = next(o for o in ontology["objects"] if o["source_entity"] == "t_order")
    assert order["name"] == "订单"
    assert any(p["semantic_type"] == "currency_cny" for p in order["properties"])

    # Step 6: Verify upsert works
    result2 = importer.import_dict(tenant_id=tenant.id, config=config)
    assert result2["objects_updated"] == 2
    assert result2["objects_created"] == 0
