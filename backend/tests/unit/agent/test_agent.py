import pytest
import json
from unittest.mock import MagicMock
from app.services.agent.react import AgentService


@pytest.fixture
def mock_ontology_context():
    return {
        "objects": [
            {
                "name": "Order",
                "description": "Customer purchase order",
                "properties": [
                    {"name": "id", "type": "integer"},
                    {"name": "total_amount", "type": "float", "semantic_type": "currency_cny"},
                ],
                "health_rules": [
                    {"metric": "avg_delivery_days", "warning": "> 3", "critical": "> 7"}
                ],
                "goals": [],
                "knowledge": [],
            }
        ],
        "relationships": [],
    }


@pytest.fixture
def mock_toolkit():
    toolkit = MagicMock()
    toolkit.get_tool_definitions.return_value = [
        {"name": "query_data", "description": "Query data", "parameters": {}},
    ]
    toolkit.execute_tool.return_value = {
        "success": True,
        "data": [{"id": 1, "total_amount": 5000}],
        "count": 1,
    }
    return toolkit


def test_build_system_prompt(mock_ontology_context, mock_toolkit):
    agent = AgentService(
        ontology_context=mock_ontology_context,
        toolkit=mock_toolkit,
    )
    prompt = agent.build_system_prompt()
    assert "Order" in prompt
    assert "total_amount" in prompt
    assert "currency_cny" in prompt


def test_build_system_prompt_includes_health_rules(mock_ontology_context, mock_toolkit):
    agent = AgentService(
        ontology_context=mock_ontology_context,
        toolkit=mock_toolkit,
    )
    prompt = agent.build_system_prompt()
    assert "avg_delivery_days" in prompt


def test_format_tool_result(mock_ontology_context, mock_toolkit):
    agent = AgentService(
        ontology_context=mock_ontology_context,
        toolkit=mock_toolkit,
    )
    result = {"success": True, "data": [{"id": 1}], "count": 1}
    formatted = agent.format_tool_result("query_data", result)
    assert "1" in formatted


def test_parse_tool_call():
    tool_call = {
        "name": "query_data",
        "arguments": json.dumps({
            "object_type": "Order",
            "limit": 10,
        }),
    }
    name, params = AgentService.parse_tool_call(tool_call)
    assert name == "query_data"
    assert params["object_type"] == "Order"
