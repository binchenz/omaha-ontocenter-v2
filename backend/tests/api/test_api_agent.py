import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models.auth.tenant import Tenant
from app.models.auth.user import User
from app.models.project.project import Project
from app.schemas.chat.agent import AgentChatResponse


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

    user = User(email="agent_test@test.com", username="agent_test", hashed_password="hashed", tenant_id=tenant.id)
    db_session.add(user)
    db_session.commit()

    project = Project(name="Agent Test Project", owner_id=user.id, tenant_id=tenant.id,
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


def test_agent_chat_endpoint_exists(client):
    test_client, project_id = client
    mock_resp = AgentChatResponse(response="测试响应")
    with patch("app.api.chat.agent.AgentService.chat", return_value=mock_resp):
        resp = test_client.post(
            f"/api/v1/agent/{project_id}/chat",
            json={"message": "列出所有业务对象"},
        )
    assert resp.status_code == 200


def test_agent_chat_returns_response_structure(client):
    test_client, project_id = client
    mock_resp = AgentChatResponse(
        response="当前有以下业务对象：Order, Customer",
        tool_calls=[],
        sources=[],
    )
    with patch("app.api.chat.agent.AgentService.chat", return_value=mock_resp):
        resp = test_client.post(
            f"/api/v1/agent/{project_id}/chat",
            json={"message": "列出所有业务对象"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
