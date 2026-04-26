import pytest
from datetime import datetime
from app.models.chat.chat_session import ChatSession, ChatMessage
from app.database import Base, engine


def test_chat_session_creation():
    """Test ChatSession model creation."""
    session = ChatSession(
        project_id=1,
        user_id=1,
        title="Test Chat"
    )
    assert session.project_id == 1
    assert session.user_id == 1
    assert session.title == "Test Chat"
    assert session.created_at is None  # Not set until DB insert


def test_chat_message_creation():
    """Test ChatMessage model creation."""
    message = ChatMessage(
        session_id=1,
        role="user",
        content="Hello"
    )
    assert message.session_id == 1
    assert message.role == "user"
    assert message.content == "Hello"
    assert message.tool_calls is None
    assert message.chart_config is None
