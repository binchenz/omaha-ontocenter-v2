import pytest
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project
from app.services.ontology.store import OntologyStore


@pytest.fixture
def client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    # Import all models so Base metadata is populated
    from app.models import tenant, user, project, ontology
    from sqlalchemy.pool import StaticPool
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Create a test user and tenant
    tenant = Tenant(name="Test Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()

    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed",
        tenant_id=tenant.id,
    )
    db_session.add(user)
    db_session.commit()

    # Create a test project (required for some endpoints)
    project = Project(name="Test Project", owner_id=user.id, tenant_id=tenant.id)
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


def test_create_ontology_object(client):
    response = client.post("/api/v1/ontology/objects", json={
        "name": "Customer",
        "source_entity": "t_customer",
        "datasource_id": "mysql_erp",
        "datasource_type": "sql",
        "description": "Customer information",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Customer"


def test_list_ontology_objects(client):
    # Create object via API first
    client.post("/api/v1/ontology/objects", json={
        "name": "Product",
        "source_entity": "t_product",
        "datasource_id": "db1",
        "datasource_type": "sql",
    })
    response = client.get("/api/v1/ontology/objects")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_ontology_object(client):
    client.post("/api/v1/ontology/objects", json={
        "name": "Order",
        "source_entity": "t_order",
        "datasource_id": "mysql_erp",
        "datasource_type": "sql",
    })
    response = client.get("/api/v1/ontology/objects/Order")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Order"


def test_delete_ontology_object(client):
    client.post("/api/v1/ontology/objects", json={
        "name": "Temp",
        "source_entity": "t_temp",
        "datasource_id": "db1",
        "datasource_type": "sql",
    })
    response = client.delete("/api/v1/ontology/objects/Temp")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_add_object_property(client):
    client.post("/api/v1/ontology/objects", json={
        "name": "Product",
        "source_entity": "t_product",
        "datasource_id": "db1",
        "datasource_type": "sql",
    })
    response = client.post("/api/v1/ontology/objects/Product/properties", json={
        "name": "price",
        "data_type": "float",
        "semantic_type": "currency_cny",
    })
    assert response.status_code == 200
    assert response.json()["name"] == "price"


def test_import_ontology_yaml(client):
    yaml_content = """
datasources:
  - id: mysql_erp
    type: sql
    connection:
      url: "sqlite:///:memory:"
ontology:
  objects:
    - name: Invoice
      datasource: mysql_erp
      source_entity: t_invoice
      properties:
        - name: amount
          type: float
  relationships: []
"""
    response = client.post("/api/v1/ontology/import", json={"config_yaml": yaml_content})
    assert response.status_code == 200
    data = response.json()
    assert data["objects_created"] == 1
    assert data["relationships_created"] == 0
