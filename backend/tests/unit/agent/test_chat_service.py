import pytest
from unittest.mock import Mock, patch
from app.services.agent.chat_service import ChatService

SEMANTIC_CONFIG = """
datasources:
  - id: test_db
    type: sqlite
    connection:
      database: ./test.db
ontology:
  objects:
    - name: Product
      datasource: test_db
      table: products
      primary_key: id
      properties:
        - name: price
          column: sale_price
          type: decimal
          semantic_type: currency
          currency: CNY
          description: "商品售价"
        - name: gross_margin
          semantic_type: computed
          formula: "(price - cost) / price"
          return_type: percentage
          description: "商品毛利率"
          business_context: "毛利率 > 30% 视为健康"
"""


def test_chat_service_initialization():
    """Test ChatService can be initialized."""
    service = ChatService(project_id=1, db=Mock())
    assert service.project_id == 1


def test_build_ontology_context():
    """Test building ontology context from project config."""
    service = ChatService(project_id=1, db=Mock())

    with patch('app.services.agent.chat_service.omaha_service') as mock_omaha:
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


def test_build_ontology_context_uses_semantic_service():
    """Test that _build_ontology_context uses semantic_service for enriched context."""
    service = ChatService(project_id=1, db=Mock())
    context = service._build_ontology_context(SEMANTIC_CONFIG)
    assert "Product" in context
    assert "CNY" in context
    assert "毛利率 > 30% 视为健康" in context
    assert "gross_margin" in context


def test_get_tool_schemas():
    """Test getting MCP tool schemas."""
    service = ChatService(project_id=1, db=Mock())
    tools = service._get_tool_schemas()

    assert len(tools) == 15
    tool_names = [t["function"]["name"] for t in tools]
    assert "list_objects" in tool_names
    assert "get_schema" in tool_names
    assert "query_data" in tool_names
    assert "assess_quality" in tool_names
    assert "clean_data" in tool_names
    assert "load_template" in tool_names
    assert "scan_tables" in tool_names
    assert "infer_ontology" in tool_names
    assert "confirm_ontology" in tool_names
    assert "edit_ontology" in tool_names


@patch('app.services.agent._legacy_chat_service.openai')
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
