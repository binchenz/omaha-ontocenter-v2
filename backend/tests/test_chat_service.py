import pytest
from unittest.mock import Mock, patch
from app.services.chat import ChatService


def test_chat_service_initialization():
    """Test ChatService can be initialized."""
    service = ChatService(project_id=1, db=Mock())
    assert service.project_id == 1


def test_build_ontology_context():
    """Test building ontology context from project config."""
    service = ChatService(project_id=1, db=Mock())

    with patch('app.services.chat.omaha_service') as mock_omaha:
        mock_omaha.build_ontology.return_value = {
            "valid": True,
            "ontology": {
                "objects": [{"name": "Product", "properties": [{"name": "id"}, {"name": "name"}]}]
            }
        }

        context = service._build_ontology_context("config_yaml")
        assert "Product" in context
        assert "id" in context
        assert "name" in context


def test_get_tool_schemas():
    """Test getting MCP tool schemas."""
    service = ChatService(project_id=1, db=Mock())
    tools = service._get_tool_schemas()

    assert len(tools) == 7
    tool_names = [t["function"]["name"] for t in tools]
    assert "list_objects" in tool_names
    assert "get_schema" in tool_names
    assert "query_data" in tool_names


@patch('app.services.chat.openai')
def test_send_message_with_openai(mock_openai):
    """Test sending message with OpenAI."""
    mock_client = Mock()
    mock_openai.OpenAI.return_value = mock_client

    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "查询结果"
    mock_response.choices[0].message.tool_calls = None
    mock_client.chat.completions.create.return_value = mock_response

    service = ChatService(project_id=1, db=Mock())

    with patch.object(service, '_load_history', return_value=[]):
        with patch.object(service, '_build_ontology_context', return_value="Product"):
            with patch.object(service, '_save_messages'):
                with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                    result = service.send_message(
                        session_id=1,
                        user_message="查询商品",
                        config_yaml="config",
                        llm_provider="openai"
                    )

                    assert result["message"] == "查询结果"
