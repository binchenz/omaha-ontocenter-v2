import pytest
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project
from app.services.ontology_store import OntologyStore


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

    # Seed an ontology object
    store = OntologyStore(db_session)
    store.create_object(tenant_id=tenant.id, name="Order",
                        source_entity="t_order", datasource_id="mysql_erp", datasource_type="sql")

    yield TestClient(app)

    app.dependency_overrides.clear()
    db_session.close()


def test_agent_query_endpoint(client):
    response = client.post("/api/v1/agent/query", json={"message": "Query all Orders"})
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "tool_calls" in data
    assert len(data["tool_calls"]) == 1


def test_agent_context_endpoint(client):
    response = client.get("/api/v1/agent/context")
    assert response.status_code == 200
    data = response.json()
    assert "context" in data
    assert "Order" in data["context"]
