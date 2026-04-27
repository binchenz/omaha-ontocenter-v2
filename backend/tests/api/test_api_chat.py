import pytest
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user
from app.database import get_db
from unittest.mock import Mock, patch


# Shared mock objects
mock_user = Mock()
mock_user.id = 1
mock_user.email = "test@test.com"
mock_user.is_active = True

mock_project = Mock()
mock_project.id = 1
mock_project.omaha_config = "config"
mock_project.owner_id = 1

mock_chat_session = Mock()
mock_chat_session.id = 1
mock_chat_session.project_id = 1
mock_chat_session.user_id = 1
mock_chat_session.title = "Test"
mock_chat_session.created_at = datetime(2026, 3, 16, 0, 0, 0)
mock_chat_session.updated_at = None


def override_get_current_user():
    return mock_user


def override_get_db():
    mock_session = Mock()
    mock_q = Mock()
    mock_q.filter.return_value.first.return_value = mock_chat_session
    mock_q.filter.return_value.order_by.return_value.all.return_value = []
    mock_session.query.return_value = mock_q
    mock_session.add = Mock()
    mock_session.commit = Mock()

    def mock_refresh(obj):
        obj.id = 1
        obj.project_id = 1
        obj.user_id = 1
        obj.title = "Test Chat"
        obj.created_at = datetime(2026, 3, 16, 0, 0, 0)
        obj.updated_at = None

    mock_session.refresh = mock_refresh
    mock_session.delete = Mock()
    yield mock_session


@pytest.fixture(autouse=True)
def apply_overrides():
    """Apply dependency overrides for this module only, clean up after each test."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


client = TestClient(app)


def test_create_chat_session():
    """Test creating a chat session."""
    with patch('app.api.chat.chat.get_project_for_owner', return_value=mock_project):
        response = client.post(
            "/api/v1/chat/1/sessions",
            json={"title": "Test Chat"},
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data


def test_list_chat_sessions():
    """Test listing chat sessions."""
    with patch('app.api.chat.chat.get_project_for_owner', return_value=mock_project):
        response = client.get(
            "/api/v1/chat/1/sessions",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


def test_send_message():
    """Test sending a message."""
    with patch('app.api.chat.chat.get_project_for_owner', return_value=mock_project):
        with patch('app.api.chat.chat.ChatServiceV2') as mock_service:
            from unittest.mock import AsyncMock
            mock_service.return_value.send_message = AsyncMock(return_value={
                "message": "测试响应",
                "data_table": None,
                "chart_config": None,
                "sql": None
            })
            response = client.post(
                "/api/v1/chat/1/sessions/1/message",
                json={"message": "查询商品"},
                headers={"Authorization": "Bearer test-token"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "测试响应"


def test_delete_chat_session():
    """Test deleting a chat session."""
    with patch('app.api.chat.chat.get_project_for_owner', return_value=mock_project):
        response = client.delete(
            "/api/v1/chat/1/sessions/1",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session deleted"
