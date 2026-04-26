import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project
from app.services.ontology.schema_scanner import TableSummary


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    tenant = Tenant(name="Test Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()

    user = User(email="auto@test.com", username="autotest", hashed_password="hashed", tenant_id=tenant.id)
    db_session.add(user)
    db_session.commit()

    project = Project(name="Auto Test", owner_id=user.id, tenant_id=tenant.id,
                      omaha_config='datasources:\n  - id: test_db\n    type: sql\n    connection:\n      url: "sqlite:///:memory:"')
    db_session.add(project)
    db_session.commit()

    from app.api.deps import get_current_user

    class FakeUser:
        def __init__(self, u):
            self.id = u.id
            self.email = u.email
            self.username = u.username
            self.tenant_id = u.tenant_id
            self.is_active = u.is_active
            self.is_superuser = u.is_superuser

    app.dependency_overrides[get_current_user] = lambda: FakeUser(user)
    yield TestClient(app), project.id
    app.dependency_overrides.clear()
    db_session.close()


def test_scan_endpoint(client):
    test_client, project_id = client
    mock_tables = [
        TableSummary(name="t_order", row_count=100,
                     columns=[{"name": "id", "type": "INTEGER", "nullable": False}],
                     sample_values={"id": ["1", "2", "3"]}),
    ]
    with patch("app.api.ontology_store_routes.SchemaScanner") as MockScanner:
        MockScanner.return_value.scan_all.return_value = mock_tables
        MockScanner.return_value.close.return_value = None
        resp = test_client.post(
            f"/api/v1/ontology-store/{project_id}/scan",
            json={"datasource_id": "test_db"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tables"]) == 1
    assert data["tables"][0]["name"] == "t_order"


def test_infer_endpoint(client):
    test_client, project_id = client
    mock_tables = [
        TableSummary(name="t_order", row_count=100,
                     columns=[{"name": "id", "type": "INTEGER", "nullable": False}],
                     sample_values={"id": ["1", "2"]}),
    ]
    from app.schemas.auto_model import InferredObject, InferredProperty
    mock_obj = InferredObject(
        name="订单", source_entity="t_order", description="订单表",
        datasource_id="test_db", datasource_type="sql",
        properties=[InferredProperty(name="id", data_type="integer", semantic_type="id")],
    )
    with patch("app.api.ontology_store_routes.SchemaScanner") as MockScanner, \
         patch("app.api.ontology_store_routes.OntologyInferrer") as MockInferrer:
        MockScanner.return_value.scan_table.return_value = mock_tables[0]
        MockScanner.return_value.close.return_value = None
        MockInferrer.return_value.infer_table.return_value = mock_obj
        MockInferrer.return_value.infer_relationships_by_naming.return_value = []
        resp = test_client.post(
            f"/api/v1/ontology-store/{project_id}/infer",
            json={"datasource_id": "test_db", "tables": ["t_order"]},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["objects"]) == 1
    assert data["objects"][0]["name"] == "订单"


def test_confirm_endpoint(client):
    test_client, project_id = client
    resp = test_client.post(
        f"/api/v1/ontology-store/{project_id}/confirm",
        json={
            "objects": [
                {
                    "name": "订单",
                    "source_entity": "t_order",
                    "description": "订单表",
                    "datasource_id": "test_db",
                    "datasource_type": "sql",
                    "properties": [
                        {"name": "id", "data_type": "integer", "semantic_type": "id"},
                        {"name": "amount", "data_type": "float", "semantic_type": "currency_cny"},
                    ],
                }
            ],
            "relationships": [],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["objects_created"] == 1
