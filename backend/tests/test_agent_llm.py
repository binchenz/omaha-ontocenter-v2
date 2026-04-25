import json
import pytest
from unittest.mock import MagicMock, patch
from app.services.agent import AgentService
from app.services.agent_tools import AgentToolkit


def _make_llm_response(content=None, tool_calls=None):
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_tool_call(name, arguments, call_id="call_1"):
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = name
    tc.function.arguments = json.dumps(arguments)
    return tc


@pytest.fixture
def ontology_context():
    return {
        "objects": [{"name": "Order", "description": "Orders", "properties": [
            {"name": "id", "type": "integer", "semantic_type": "id"},
            {"name": "amount", "type": "float", "semantic_type": "currency_cny"},
        ], "health_rules": [], "goals": [], "knowledge": []}],
        "relationships": [],
    }


@pytest.fixture
def toolkit():
    omaha = MagicMock()
    omaha.query_objects.return_value = {
        "success": True, "data": [{"id": 1, "amount": 500}], "count": 1, "sql": "SELECT *",
    }
    return AgentToolkit(omaha_service=omaha)


def test_chat_no_tool_call(ontology_context, toolkit):
    agent = AgentService(ontology_context=ontology_context, toolkit=toolkit)
    resp_no_tools = _make_llm_response(content="订单总额是500元。")
    with patch.object(agent, "_call_llm", return_value=resp_no_tools):
        result = agent.chat("订单总额多少？")
    assert result.response == "订单总额是500元。"
    assert result.data_table is None


def test_chat_with_tool_call(ontology_context, toolkit):
    agent = AgentService(ontology_context=ontology_context, toolkit=toolkit)
    tool_call = _make_tool_call("query_data", {"object_type": "Order", "limit": 10})
    resp_with_tool = _make_llm_response(content="", tool_calls=[tool_call])
    resp_final = _make_llm_response(content="查询到1条订单，金额500元。")

    call_count = [0]
    def side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return resp_with_tool
        return resp_final

    with patch.object(agent, "_call_llm", side_effect=side_effect):
        result = agent.chat("查一下订单")
    assert "500" in result.response
    assert result.data_table is not None
    assert result.sql == "SELECT *"
    assert len(result.tool_calls) == 1


def test_chat_max_iterations(ontology_context, toolkit):
    agent = AgentService(ontology_context=ontology_context, toolkit=toolkit)
    tool_call = _make_tool_call("list_objects", {})
    resp_loop = _make_llm_response(content="", tool_calls=[tool_call])
    with patch.object(agent, "_call_llm", return_value=resp_loop):
        result = agent.chat("test")
    assert "最大迭代次数" in result.response


def test_chat_tool_error(ontology_context):
    omaha = MagicMock()
    omaha.query_objects.side_effect = Exception("DB connection failed")
    toolkit = AgentToolkit(omaha_service=omaha)
    agent = AgentService(ontology_context=ontology_context, toolkit=toolkit)

    tool_call = _make_tool_call("query_data", {"object_type": "Order"})
    resp_tool = _make_llm_response(content="", tool_calls=[tool_call])
    resp_final = _make_llm_response(content="查询失败，请稍后重试。")

    calls = [0]
    def side_effect(*args, **kwargs):
        calls[0] += 1
        return resp_tool if calls[0] == 1 else resp_final

    with patch.object(agent, "_call_llm", side_effect=side_effect):
        result = agent.chat("查订单")
    assert result.response is not None


def test_build_tools_schema(ontology_context, toolkit):
    agent = AgentService(ontology_context=ontology_context, toolkit=toolkit)
    schema = agent._build_tools_schema()
    assert isinstance(schema, list)
    assert all(t["type"] == "function" for t in schema)
    names = {t["function"]["name"] for t in schema}
    assert "query_data" in names
    assert "generate_chart" in names
