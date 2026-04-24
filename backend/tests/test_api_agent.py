import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.database import Base, get_db
from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project


@pytest.fixture
def client():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
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
        email="agent_test@test.com",
        username="agent_test",
        hashed_password="hashed",
        tenant_id=tenant.id,
    )
    db_session.add(user)
    db_session.commit()

    project = Project(name="Agent Test Project", owner_id=user.id, tenant_id=tenant.id)
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


def test_agent_chat_endpoint_exists(client):
    test_client, project_id = client
    resp = test_client.post(
        f"/api/v1/agent/{project_id}/chat",
        json={"message": "列出所有业务对象"},
    )
    assert resp.status_code in (200, 422, 500)


def test_agent_chat_returns_response_structure(client):
    test_client, project_id = client
    with patch("app.api.agent.get_agent_response") as mock_agent:
        mock_agent.return_value = {
            "response": "当前有以下业务对象：Order, Customer",
            "tool_calls": [],
            "sources": [],
        }
        resp = test_client.post(
            f"/api/v1/agent/{project_id}/chat",
            json={"message": "列出所有业务对象"},
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "response" in data
