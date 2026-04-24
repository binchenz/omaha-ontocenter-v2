import pytest
from unittest.mock import MagicMock
from app.services.agent_tools import AgentToolkit


@pytest.fixture
def mock_omaha_service():
    service = MagicMock()
    service.query_objects.return_value = {
        "success": True,
        "data": [
            {"name": "Product A", "amount": 1000},
            {"name": "Product B", "amount": 2000},
        ],
        "count": 2,
    }
    service.build_ontology.return_value = {
        "objects": [
            {"name": "Order", "fields": [{"name": "amount", "type": "float"}]},
        ],
    }
    return service


@pytest.fixture
def toolkit(mock_omaha_service):
    return AgentToolkit(omaha_service=mock_omaha_service)


def test_tool_definitions(toolkit):
    tools = toolkit.get_tool_definitions()
    tool_names = {t["name"] for t in tools}
    assert "query_data" in tool_names
    assert "list_objects" in tool_names
    assert "get_schema" in tool_names


def test_query_data_tool(toolkit, mock_omaha_service):
    result = toolkit.execute_tool("query_data", {
        "object_type": "Order",
        "filters": [{"field": "status", "operator": "=", "value": "active"}],
        "columns": ["name", "amount"],
        "limit": 10,
    })
    assert result["success"] is True
    assert len(result["data"]) == 2
    mock_omaha_service.query_objects.assert_called_once()


def test_list_objects_tool(toolkit, mock_omaha_service):
    result = toolkit.execute_tool("list_objects", {})
    assert "objects" in result


def test_unknown_tool_returns_error(toolkit):
    result = toolkit.execute_tool("nonexistent_tool", {})
    assert result["success"] is False
    assert "error" in result
