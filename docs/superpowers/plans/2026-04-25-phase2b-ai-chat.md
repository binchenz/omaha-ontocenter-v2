# Phase 2b: AI Chat — AgentService LLM Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire real LLM calling (ReAct loop with tool execution) into AgentService, replacing the placeholder response. ChatService delegates to AgentService for all LLM interactions.

**Architecture:** Migrate the ReAct loop from ChatService._call_openai_compatible() into AgentService.chat(). Add generate_chart tool to AgentToolkit. Slim ChatService.send_message() to: load history -> call AgentService.chat() -> save messages. Both /chat and /agent endpoints use AgentService.

**Tech Stack:** FastAPI, OpenAI SDK (for Deepseek/OpenAI), Anthropic SDK, pytest, unittest.mock

**Spec Reference:** `docs/superpowers/specs/2026-04-25-phase2b-ai-chat-design.md`

---

## File Structure

### Modified Files
- `backend/app/schemas/agent.py` — Extend AgentChatResponse with data_table, chart_config, sql
- `backend/app/services/agent_tools.py` — Add generate_chart tool
- `backend/app/services/agent.py` — Add chat(), _react_loop(), _call_llm(), _build_tools_schema()
- `backend/app/services/chat.py` — Slim send_message() to delegate to AgentService
- `backend/app/api/agent.py` — Replace placeholder with AgentService.chat()

### New Files
- `backend/tests/test_agent_llm.py` — ReAct loop tests (mock LLM)
- `backend/tests/test_agent_chart.py` — generate_chart tool tests
- `backend/tests/test_chat_refactor.py` — ChatService delegation regression tests

---

## Task 1: Extend AgentChatResponse Schema

**Files:**
- Modify: `backend/app/schemas/agent.py`

- [ ] **Step 1: Update the schema**

Replace `backend/app/schemas/agent.py` with:

```python
from pydantic import BaseModel
from typing import Optional


class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ToolCallRecord(BaseModel):
    tool_name: str
    params: dict
    result_summary: str


class AgentChatResponse(BaseModel):
    response: str
    tool_calls: list[ToolCallRecord] = []
    sources: list[str] = []
    data_table: list[dict] | None = None
    chart_config: dict | None = None
    sql: str | None = None
```

- [ ] **Step 2: Verify import**

Run: `cd backend && python -c "from app.schemas.agent import AgentChatResponse; r = AgentChatResponse(response='test', data_table=[{'a':1}]); print(r.data_table)"`
Expected: `[{'a': 1}]`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/agent.py
git commit -m "feat(phase2b): extend AgentChatResponse with data_table, chart_config, sql"
```

---

## Task 2: Add generate_chart Tool to AgentToolkit

**Files:**
- Modify: `backend/app/services/agent_tools.py`
- Test: `backend/tests/test_agent_chart.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_agent_chart.py
from app.services.agent_tools import AgentToolkit
from unittest.mock import MagicMock


def test_generate_chart_bar():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    result = toolkit.execute_tool("generate_chart", {
        "data": [
            {"name": "Product A", "sales": 1000},
            {"name": "Product B", "sales": 2000},
            {"name": "Product C", "sales": 1500},
        ],
        "chart_type": "bar",
        "title": "Sales by Product",
        "x_field": "name",
        "y_field": "sales",
    })
    assert result["success"] is True
    config = result["chart_config"]
    assert config["series"][0]["type"] == "bar"
    assert len(config["xAxis"]["data"]) == 3


def test_generate_chart_line():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    result = toolkit.execute_tool("generate_chart", {
        "data": [
            {"month": "Jan", "revenue": 100},
            {"month": "Feb", "revenue": 150},
        ],
        "chart_type": "line",
        "title": "Monthly Revenue",
        "x_field": "month",
        "y_field": "revenue",
    })
    assert result["success"] is True
    assert result["chart_config"]["series"][0]["type"] == "line"


def test_generate_chart_pie():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    result = toolkit.execute_tool("generate_chart", {
        "data": [
            {"category": "A", "value": 30},
            {"category": "B", "value": 70},
        ],
        "chart_type": "pie",
        "title": "Distribution",
        "x_field": "category",
        "y_field": "value",
    })
    assert result["success"] is True
    series = result["chart_config"]["series"][0]
    assert series["type"] == "pie"
    assert len(series["data"]) == 2


def test_generate_chart_empty_data():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    result = toolkit.execute_tool("generate_chart", {
        "data": [],
        "chart_type": "bar",
        "x_field": "name",
        "y_field": "value",
    })
    assert result["success"] is True


def test_tool_definitions_include_chart():
    toolkit = AgentToolkit(omaha_service=MagicMock())
    names = {t["name"] for t in toolkit.get_tool_definitions()}
    assert "generate_chart" in names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_agent_chart.py -v`
Expected: FAIL — generate_chart not found

- [ ] **Step 3: Add generate_chart to AgentToolkit**

Replace `backend/app/services/agent_tools.py` with:

```python
from typing import Any


class AgentToolkit:
    def __init__(self, omaha_service):
        self.omaha_service = omaha_service
        self._tools = {
            "query_data": self._query_data,
            "list_objects": self._list_objects,
            "get_schema": self._get_schema,
            "generate_chart": self._generate_chart,
        }

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "name": "query_data",
                "description": "Query data from a business object. Use this to retrieve records with optional filters and column selection.",
                "parameters": {
                    "object_type": {"type": "string", "description": "Name of the object to query", "required": True},
                    "columns": {"type": "array", "description": "Columns to return. Omit for all columns.", "required": False},
                    "filters": {"type": "array", "description": "Filter conditions: [{field, operator, value}]", "required": False},
                    "limit": {"type": "integer", "description": "Max rows to return (default 100)", "required": False},
                },
            },
            {
                "name": "list_objects",
                "description": "List all available business objects and their descriptions.",
                "parameters": {},
            },
            {
                "name": "get_schema",
                "description": "Get the schema (fields, types, semantic types) of a business object.",
                "parameters": {
                    "object_type": {"type": "string", "description": "Name of the object", "required": True},
                },
            },
            {
                "name": "generate_chart",
                "description": "Generate an ECharts chart config from query result data. Call this after query_data to visualize results.",
                "parameters": {
                    "data": {"type": "array", "description": "Array of data rows from query_data result", "required": True},
                    "chart_type": {"type": "string", "description": "Chart type: bar, line, pie, scatter", "required": True},
                    "title": {"type": "string", "description": "Chart title", "required": False},
                    "x_field": {"type": "string", "description": "Field name for X axis", "required": True},
                    "y_field": {"type": "string", "description": "Field name for Y axis / values", "required": True},
                },
            },
        ]

    def execute_tool(self, tool_name: str, params: dict[str, Any]) -> dict:
        handler = self._tools.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        try:
            return handler(params)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _query_data(self, params: dict) -> dict:
        return self.omaha_service.query_objects(
            object_type=params["object_type"],
            selected_columns=params.get("columns"),
            filters=params.get("filters"),
            limit=params.get("limit", 100),
        )

    def _list_objects(self, params: dict) -> dict:
        ontology = self.omaha_service.build_ontology()
        return {"success": True, "objects": ontology.get("objects", [])}

    def _get_schema(self, params: dict) -> dict:
        schema = self.omaha_service.get_object_schema(params["object_type"])
        if schema:
            return {"success": True, "schema": schema}
        return {"success": False, "error": f"Object '{params['object_type']}' not found"}

    def _generate_chart(self, params: dict) -> dict:
        data = params.get("data", [])
        chart_type = params.get("chart_type", "bar")
        title = params.get("title", "")
        x_field = params.get("x_field", "")
        y_field = params.get("y_field", "")

        if chart_type == "pie":
            chart_config = {
                "title": {"text": title},
                "tooltip": {"trigger": "item"},
                "series": [{
                    "type": "pie",
                    "data": [
                        {"name": str(row.get(x_field, "")), "value": row.get(y_field, 0)}
                        for row in data
                    ],
                }],
            }
        else:
            chart_config = {
                "title": {"text": title},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": [str(row.get(x_field, "")) for row in data]},
                "yAxis": {"type": "value"},
                "series": [{"type": chart_type, "data": [row.get(y_field, 0) for row in data]}],
            }
        return {"success": True, "chart_config": chart_config}
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_agent_chart.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent_tools.py backend/tests/test_agent_chart.py
git commit -m "feat(phase2b): add generate_chart tool to AgentToolkit"
```

---

## Task 3: AgentService LLM Integration — ReAct Loop

**Files:**
- Modify: `backend/app/services/agent.py`
- Test: `backend/tests/test_agent_llm.py`

- [ ] **Step 1: Write failing tests for ReAct loop**

```python
# backend/tests/test_agent_llm.py
import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
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
    assert "超时" in result.response or "迭代" in result.response


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_agent_llm.py -v`
Expected: FAIL — `AgentService has no attribute 'chat'`

- [ ] **Step 3: Implement AgentService.chat() with ReAct loop**

Replace `backend/app/services/agent.py` entirely with the new version that adds chat(), _react_loop(), _call_llm(), _build_tools_schema(). Keep all existing methods (build_system_prompt, format_tool_result, parse_tool_call, all _format_* methods).

Add these imports at the top:

```python
import json
import os
from typing import Any, Optional
from dataclasses import dataclass, field
```

Add after the existing `AgentService.__init__`:

```python
    # Add provider param to __init__
    def __init__(self, ontology_context: dict, toolkit, tenant_knowledge: list[str] = None, provider: str = None):
        self.ontology_context = ontology_context
        self.toolkit = toolkit
        self.tenant_knowledge = tenant_knowledge or []
        self.provider = provider or self._detect_provider()

    def _detect_provider(self) -> str:
        from app.config import settings
        if settings.DEEPSEEK_API_KEY:
            return "deepseek"
        if settings.OPENAI_API_KEY:
            return "openai"
        if settings.ANTHROPIC_API_KEY:
            return "anthropic"
        return "deepseek"
```

Add the chat method and supporting methods:

```python
    def chat(self, message: str, history: list[dict] = None) -> "AgentResponse":
        system_prompt = self.build_system_prompt()
        tools_schema = self._build_tools_schema()

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages += history
        messages.append({"role": "user", "content": message})

        return self._react_loop(messages, tools_schema)

    def _react_loop(self, messages: list[dict], tools_schema: list[dict], max_iterations: int = 8) -> "AgentResponse":
        from app.schemas.agent import AgentChatResponse, ToolCallRecord
        tool_calls_log = []
        data_table = None
        chart_config = None
        sql = None

        for iteration in range(max_iterations):
            response = self._call_llm(messages, tools_schema)

            if not response.tool_calls:
                return AgentChatResponse(
                    response=response.content or "",
                    tool_calls=tool_calls_log,
                    data_table=data_table,
                    chart_config=chart_config,
                    sql=sql,
                )

            messages.append({
                "role": "assistant",
                "content": response.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in response.tool_calls
                ],
            })

            for tc in response.tool_calls:
                name = tc.function.name
                try:
                    params = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    params = {}

                result = self.toolkit.execute_tool(name, params)

                tool_calls_log.append(ToolCallRecord(
                    tool_name=name, params=params,
                    result_summary=f"success={result.get('success', False)}",
                ))

                if name == "query_data" and result.get("data"):
                    data_table = result["data"]
                    sql = result.get("sql")
                if name == "generate_chart" and result.get("chart_config"):
                    chart_config = result["chart_config"]

                tool_content = self.format_tool_result(name, result)
                if name == "query_data" and result.get("success") and result.get("data"):
                    tool_content += "\n\n请基于以上数据直接回答用户问题。"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_content,
                })

        return AgentChatResponse(
            response="分析完成，但达到了最大迭代次数。",
            tool_calls=tool_calls_log,
            data_table=data_table,
            chart_config=chart_config,
            sql=sql,
        )

    def _call_llm(self, messages: list[dict], tools_schema: list[dict]):
        from app.config import settings
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai package required: pip install openai")

        if self.provider == "deepseek":
            client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)
            model = settings.DEEPSEEK_MODEL
        elif self.provider == "openai":
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            model = "gpt-4o-mini"
        else:
            client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)
            model = settings.DEEPSEEK_MODEL

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools_schema if tools_schema else None,
            temperature=0.1,
        )
        return response.choices[0].message

    def _build_tools_schema(self) -> list[dict]:
        tools = []
        for tool_def in self.toolkit.get_tool_definitions():
            properties = {}
            required = []
            for pname, pdef in tool_def.get("parameters", {}).items():
                properties[pname] = {
                    "type": pdef["type"],
                    "description": pdef.get("description", ""),
                }
                if pdef.get("required"):
                    required.append(pname)
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_def["name"],
                    "description": tool_def["description"],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })
        return tools
```

- [ ] **Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_agent_llm.py -v`
Expected: All 5 PASS

- [ ] **Step 5: Run existing agent tests for regression**

Run: `cd backend && python -m pytest tests/test_agent.py tests/test_agent_tools.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent.py backend/tests/test_agent_llm.py
git commit -m "feat(phase2b): add ReAct loop and LLM calling to AgentService"
```

---

## Task 4: Update Agent API Endpoint

**Files:**
- Modify: `backend/app/api/agent.py`

- [ ] **Step 1: Replace placeholder with real AgentService.chat()**

Replace the `agent_chat` endpoint and remove `get_agent_response`:

```python
# In backend/app/api/agent.py, replace the agent_chat function:

@router.post("/{project_id}/chat", response_model=AgentChatResponse)
def agent_chat(
    project_id: int,
    request: AgentChatRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    project = get_project_for_owner(project_id, current_user, db)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    store = OntologyStore(db)
    tenant_id = project.tenant_id or project.owner_id
    ontology_context = store.get_full_ontology(tenant_id)

    omaha_service = OmahaService(project.omaha_config or "")
    toolkit = AgentToolkit(omaha_service=omaha_service)

    agent = AgentService(
        ontology_context=ontology_context,
        toolkit=toolkit,
    )

    result = agent.chat(request.message)
    return result
```

Delete the `get_agent_response` function entirely.

- [ ] **Step 2: Run existing API tests**

Run: `cd backend && python -m pytest tests/test_api_agent.py -v`
Expected: PASS (may need minor adjustments if tests relied on placeholder text)

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/agent.py
git commit -m "feat(phase2b): wire agent API endpoint to real AgentService.chat()"
```

---

## Task 5: Slim ChatService — Delegate to AgentService

**Files:**
- Modify: `backend/app/services/chat.py`
- Test: `backend/tests/test_chat_refactor.py`

- [ ] **Step 1: Write test for ChatService delegation**

```python
# backend/tests/test_chat_refactor.py
import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.services.chat import ChatService
from app.schemas.agent import AgentChatResponse


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_send_message_delegates_to_agent(db_session):
    service = ChatService(project_id=1, db=db_session)

    mock_response = AgentChatResponse(
        response="订单总额500元",
        data_table=[{"id": 1, "amount": 500}],
        sql="SELECT * FROM t_order",
    )

    with patch("app.services.chat.AgentService") as MockAgent, \
         patch.object(service, "_load_history", return_value=[]), \
         patch.object(service, "_save_messages"):
        MockAgent.return_value.chat.return_value = mock_response
        result = service.send_message(
            session_id=1,
            user_message="查订单",
            config_yaml="datasources: []",
        )

    assert result["message"] == "订单总额500元"
    assert result["data_table"] == [{"id": 1, "amount": 500}]
    assert result["sql"] == "SELECT * FROM t_order"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_chat_refactor.py -v`
Expected: FAIL (ChatService.send_message still has old implementation)

- [ ] **Step 3: Refactor ChatService.send_message()**

In `backend/app/services/chat.py`, replace the `send_message` method (lines 587-645) with:

```python
    def send_message(
        self,
        session_id: int,
        user_message: str,
        config_yaml: str,
        llm_provider: str = "deepseek"
    ) -> Dict[str, Any]:
        from app.services.ontology_store import OntologyStore
        from app.services.agent_tools import AgentToolkit
        from app.services.agent import AgentService
        from app.services.omaha import OmahaService

        history = self._load_history(session_id, limit=20)

        omaha_svc = OmahaService(config_yaml)
        toolkit = AgentToolkit(omaha_service=omaha_svc)

        store = OntologyStore(self.db)
        project = self.db.query(ChatSession).filter_by(id=session_id).first()
        tenant_id = 1
        if project:
            from app.models.project import Project
            proj = self.db.query(Project).filter_by(id=self.project_id).first()
            if proj:
                tenant_id = proj.tenant_id or proj.owner_id

        ontology_context = store.get_full_ontology(tenant_id)

        agent = AgentService(
            ontology_context=ontology_context,
            toolkit=toolkit,
            provider=llm_provider,
        )

        try:
            result = agent.chat(user_message, history)
            response_text = result.response
            data_table = result.data_table
            chart_config = result.chart_config
            sql = result.sql
        except Exception as e:
            response_text = f"抱歉，处理您的请求时出错：{str(e)}"
            data_table = None
            chart_config = None
            sql = None

        self._save_messages(session_id, user_message, response_text, chart_config=chart_config)

        return {
            "message": response_text,
            "data_table": data_table,
            "chart_config": chart_config,
            "sql": sql,
        }
```

- [ ] **Step 4: Run test**

Run: `cd backend && python -m pytest tests/test_chat_refactor.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite for regression**

Run: `cd backend && python -m pytest tests/ --ignore=tests/integration/test_phase31_mcp.py -v --tb=short`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/chat.py backend/tests/test_chat_refactor.py
git commit -m "refactor(phase2b): slim ChatService.send_message() to delegate to AgentService"
```

---

## Task 6: Integration Verification

- [ ] **Step 1: Run full test suite**

Run: `cd backend && python -m pytest tests/ --ignore=tests/integration/test_phase31_mcp.py -v --tb=short`
Expected: All PASS

- [ ] **Step 2: Verify Swagger endpoints**

Start server: `cd backend && uvicorn app.main:app --reload --port 8000`

Check `http://localhost:8000/docs`:
- `POST /api/v1/agent/{project_id}/chat` — should show AgentChatResponse with data_table, chart_config, sql fields
- `POST /api/v1/chat/{project_id}/sessions/{session_id}/message` — should still work

- [ ] **Step 3: Commit any remaining fixes**

```bash
git add -A
git commit -m "chore(phase2b): Phase 2b complete — AgentService LLM integration"
```
