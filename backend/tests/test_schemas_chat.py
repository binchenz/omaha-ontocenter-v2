import pytest
from pydantic import ValidationError
from app.schemas.chat import ChatSessionCreate, ChatMessageCreate, ChatMessageResponse, SendMessageRequest


def test_chat_session_create_valid():
    """Test valid ChatSessionCreate schema."""
    data = {"user_id": 1, "title": "Test"}
    session = ChatSessionCreate(**data)
    assert session.user_id == 1
    assert session.title == "Test"


def test_chat_message_create_valid():
    """Test valid ChatMessageCreate schema."""
    data = {"session_id": 1, "content": "Hello"}
    message = ChatMessageCreate(**data)
    assert message.session_id == 1
    assert message.content == "Hello"


def test_chat_message_create_missing_content():
    """Test ChatMessageCreate requires content."""
    with pytest.raises(ValidationError):
        ChatMessageCreate(session_id=1)


def test_send_message_request_valid():
    """Test valid SendMessageRequest schema."""
    data = {"message": "查询商品"}
    request = SendMessageRequest(**data)
    assert request.message == "查询商品"
