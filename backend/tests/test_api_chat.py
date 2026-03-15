import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from unittest.mock import Mock, patch


client = TestClient(app)


def test_create_chat_session():
    """Test creating a chat session."""
    with patch('app.api.chat.get_db') as mock_db:
        mock_session = Mock()
        mock_query = Mock()
        mock_project = Mock()
        mock_query.filter.return_value.first.return_value = mock_project
        mock_session.query.return_value = mock_query
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        mock_db.return_value = mock_session

        response = client.post(
            "/api/v1/chat/1/sessions",
            json={"user_id": 1, "title": "Test Chat"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data


def test_list_chat_sessions():
    """Test listing chat sessions."""
    with patch('app.api.chat.get_db') as mock_db:
        mock_session = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_db.return_value = mock_session

        response = client.get("/api/v1/chat/1/sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


def test_send_message():
    """Test sending a message."""
    with patch('app.api.chat.get_db') as mock_db:
        with patch('app.api.chat.ChatService') as mock_service:
            mock_session_obj = Mock()
            mock_chat_session = Mock()
            mock_project = Mock()
            mock_project.omaha_config = "config"
            mock_project.id = 1

            # Mock query to return different results based on model
            def query_side_effect(model):
                mock_q = Mock()
                mock_filter = Mock()
                mock_first = Mock()

                if hasattr(model, '__name__'):
                    if model.__name__ == 'ChatSession':
                        mock_first.return_value = mock_chat_session
                    elif model.__name__ == 'Project':
                        mock_first.return_value = mock_project
                    else:
                        mock_first.return_value = None
                else:
                    mock_first.return_value = None

                mock_filter.first = mock_first
                mock_q.filter.return_value = mock_filter
                return mock_q

            mock_session_obj.query = query_side_effect
            mock_db.return_value = mock_session_obj

            mock_service.return_value.send_message.return_value = {
                "message": "测试响应",
                "data_table": None,
                "chart_config": None,
                "sql": None
            }

            response = client.post(
                "/api/v1/chat/1/sessions/1/message",
                json={"message": "查询商品"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "测试响应"


def test_delete_chat_session():
    """Test deleting a chat session."""
    with patch('app.api.chat.get_db') as mock_db:
        mock_session_obj = Mock()
        mock_query = Mock()
        mock_chat_session = Mock()
        mock_query.filter.return_value.first.return_value = mock_chat_session
        mock_session_obj.query.return_value = mock_query
        mock_session_obj.delete = Mock()
        mock_session_obj.commit = Mock()
        mock_db.return_value = mock_session_obj

        response = client.delete("/api/v1/chat/1/sessions/1")

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Session deleted"
