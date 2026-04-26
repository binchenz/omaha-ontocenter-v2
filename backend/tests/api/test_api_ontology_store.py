import pytest
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import app
from app.models.auth.tenant import Tenant
from app.models.auth.user import User
from app.models.project.project import Project
from app.services.ontology.store import OntologyStore


@pytest.fixture
def client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app import models as _app_models  # noqa: F401 -- ensures Base.metadata is populated
    from sqlalchemy.pool import StaticPool
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db_session = Session()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    tenant = Tenant(name="Test Corp", plan="free")
    db_session.add(tenant)
    db_session.commit()

    user = User(
        email="onto_test@test.com",
        username="onto_test",
        hashed_password="hashed",
        tenant_id=tenant.id,
    )
    db_session.add(user)
    db_session.commit()

    project = Project(name="Onto Test Project", owner_id=user.id, tenant_id=tenant.id)
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

    yield TestClient(app), project.id

    app.dependency_overrides.clear()
    db_session.close()


def test_import_yaml_endpoint(client):
    test_client, project_id = client
    yaml_content = """
datasources:
  - id: test_db
    type: sql
    connection:
      url: "sqlite:///:memory:"
ontology:
  objects:
    - name: Product
      datasource: test_db
      source_entity: t_product
      properties:
        - name: name
          type: string
        - name: price
          type: float
          semantic_type: currency_cny
  relationships: []
"""
    resp = test_client.post(
        f"/api/v1/ontology-store/{project_id}/import",
        json={"yaml_content": yaml_content},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["objects_created"] == 1


def test_list_objects_endpoint(client):
    test_client, project_id = client
    resp = test_client.get(
        f"/api/v1/ontology-store/{project_id}/objects",
    )
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_full_ontology_endpoint(client):
    test_client, project_id = client
    resp = test_client.get(
        f"/api/v1/ontology-store/{project_id}/full",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "objects" in data
    assert "relationships" in data
