import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models.auth.tenant import Tenant
from app.models.auth.user import User
from app.models.project.project import Project
from app.services.ontology.store import OntologyStore


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    tenant = Tenant(name="Acme Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()

    user = User(
        email="admin@acme.com",
        username="admin",
        hashed_password="hashed",
        tenant_id=tenant.id,
    )
    db_session.add(user)
    db_session.commit()

    project = Project(name="Main Project", owner_id=user.id, tenant_id=tenant.id)
    db_session.add(project)
    db_session.commit()

    from app.api.deps import get_current_user

    class FakeUser:
        def __init__(self, user_obj):
            self.id = user_obj.id
            self.email = user_obj.email
            self.username = user_obj.username
            self.tenant_id = user_obj.tenant_id
            self.is_active = user_obj.is_active
            self.is_superuser = user_obj.is_superuser

    fake_user = FakeUser(user)

    def override_get_current_user():
        return fake_user

    app.dependency_overrides[get_current_user] = override_get_current_user

    yield TestClient(app)

    app.dependency_overrides.clear()
    db_session.close()


def test_full_e2e_flow(client):
    """Step-by-step full flow: create object, add properties, query agent, validate schema."""

    # Step 1: Create an ontology object via API
    response = client.post("/api/v1/ontology/objects", json={
        "name": "Order",
        "source_entity": "t_order",
        "datasource_id": "mysql_erp",
        "datasource_type": "sql",
        "description": "Customer purchase order",
        "domain": "retail",
    })
    assert response.status_code == 200

    # Step 2: Add properties
    response = client.post("/api/v1/ontology/objects/Order/properties", json={
        "name": "total_amount",
        "data_type": "float",
        "semantic_type": "currency_cny",
    })
    assert response.status_code == 200

    # Step 3: Query agent
    response = client.post("/api/v1/agent/query", json={"message": "Show me the schema of Order"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["tool_calls"]) == 1
    assert data["tool_calls"][0]["tool"] == "get_ontology_schema"

    # Step 4: Get context
    response = client.get("/api/v1/agent/context")
    assert response.status_code == 200
    assert "Order" in response.json()["context"]

    # Step 5: List objects
    response = client.get("/api/v1/ontology/objects")
    assert response.status_code == 200
    objects = response.json()
    assert len(objects) == 1
    assert objects[0]["name"] == "Order"

    # Step 6: Get object detail
    response = client.get("/api/v1/ontology/objects/Order")
    assert response.status_code == 200
    obj = response.json()
    assert obj["domain"] == "retail"
    assert any(p["name"] == "total_amount" for p in obj["properties"])

    # Step 7: Delete object
    response = client.delete("/api/v1/ontology/objects/Order")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    # Step 8: Confirm deletion
    response = client.get("/api/v1/ontology/objects/Order")
    assert response.status_code == 404
