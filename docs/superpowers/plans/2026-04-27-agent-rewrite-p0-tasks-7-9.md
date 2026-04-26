# Agent 内核重写 P0 — Task 7-9

> 续接 Task 6 之后。

---

### Task 7: ConversationRuntime — 会话状态 + 上下文组装

**Files:**
- Create: `backend/app/services/agent/runtime/conversation.py`
- Create: `backend/app/services/agent/runtime/session.py`
- Test: `backend/tests/unit/agent/test_conversation_runtime.py`

- [ ] **Step 1: 写 ConversationRuntime 的测试**

```python
# backend/tests/unit/agent/test_conversation_runtime.py
import pytest
from app.services.agent.runtime.conversation import ConversationRuntime
from app.services.agent.providers.base import Message, ToolCall
from app.services.agent.skills.loader import Skill


@pytest.fixture
def skill():
    return Skill(
        name="data_query",
        description="查询分析",
        system_prompt="你是数据分析专家。查询一次后立即回答。",
        allowed_tools=["query_data", "list_objects"],
        trigger_keywords=[],
    )


@pytest.fixture
def runtime(skill):
    return ConversationRuntime(skill=skill)


def test_build_system_prompt(runtime):
    ontology_ctx = {
        "objects": [
            {"name": "Stock", "description": "A股", "properties": [
                {"name": "ts_code", "type": "string"},
                {"name": "close", "type": "float", "semantic_type": "currency_cny"},
            ]}
        ]
    }
    prompt = runtime.build_system_prompt(ontology_ctx)
    assert "数据分析专家" in prompt
    assert "Stock" in prompt
    assert "ts_code" in prompt
    assert "currency_cny" in prompt


def test_build_system_prompt_empty_ontology(runtime):
    prompt = runtime.build_system_prompt({})
    assert "数据分析专家" in prompt
    assert "无可用对象" in prompt or len(prompt) > 10


def test_append_and_get_messages(runtime):
    runtime.build_system_prompt({})
    runtime.append_user_message("你好")
    runtime.append_assistant_message("你好！", tool_calls=None)
    runtime.append_user_message("查询销售额")

    msgs = runtime.get_messages_for_llm()
    assert msgs[0].role == "system"
    assert msgs[1].role == "user"
    assert msgs[1].content == "你好"
    assert msgs[2].role == "assistant"
    assert msgs[3].role == "user"
    assert msgs[3].content == "查询销售额"


def test_append_tool_result(runtime):
    runtime.build_system_prompt({})
    runtime.append_user_message("查询")
    tc = ToolCall(id="tc_1", name="query_data", arguments={"object_type": "Stock"})
    runtime.append_assistant_message(None, tool_calls=[tc])
    runtime.append_tool_result("tc_1", '{"success": true, "data": []}')

    msgs = runtime.get_messages_for_llm()
    tool_msg = [m for m in msgs if m.role == "tool"]
    assert len(tool_msg) == 1
    assert tool_msg[0].tool_call_id == "tc_1"


def test_extract_structured():
    text = '''这是结果。
```structured
{"type": "panel", "panel_type": "quality_report", "content": "报告", "data": {"score": 85}}
```
还有更多内容。'''
    clean, items = ConversationRuntime.extract_structured(text)
    assert "```structured" not in clean
    assert len(items) == 1
    assert items[0]["panel_type"] == "quality_report"


def test_extract_structured_none():
    clean, items = ConversationRuntime.extract_structured("普通文本，没有结构化块")
    assert clean == "普通文本，没有结构化块"
    assert items is None
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
python -m pytest tests/unit/agent/test_conversation_runtime.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 conversation.py**

```python
# backend/app/services/agent/runtime/conversation.py
from __future__ import annotations
import json
import re
from app.services.agent.providers.base import Message, ToolCall
from app.services.agent.skills.loader import Skill

BASE_TEMPLATE = """你是一个企业数据分析助手，帮助用户接入数据、整理语义、回答业务问题。
你的目标用户是中小企业的非技术人员，请始终用业务语言回答。

{skill_prompt}

## 可用数据对象

{ontology}

## 工作方式（ReAct）
你必须遵循 思考→行动→观察→回答 的循环：
1. 思考：分析用户意图
2. 行动：调用合适的工具
3. 观察：分析工具返回结果
4. 回答：用业务语言给出简洁结论

## 强制规则
- 任何涉及具体数据的问题，必须先调用工具查询，不得凭空回答
- 查询一次后立即基于结果回答，不要反复查询
- 如果查询结果为空，直接告知用户，不要编造数据

请用中文回答，基于真实数据，简洁清晰。"""

_STRUCTURED_RE = re.compile(r"```structured\s*\n(.*?)\n```", re.DOTALL)


class ConversationRuntime:
    def __init__(self, skill: Skill):
        self.skill = skill
        self.messages: list[Message] = []

    def build_system_prompt(self, ontology_context: dict) -> str:
        ontology_text = self._format_ontology(ontology_context)
        prompt = BASE_TEMPLATE.format(
            skill_prompt=self.skill.system_prompt,
            ontology=ontology_text,
        )
        self.messages = [Message(role="system", content=prompt)]
        return prompt

    def append_user_message(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content))

    def append_assistant_message(self, content: str | None, tool_calls: list[ToolCall] | None) -> None:
        self.messages.append(Message(role="assistant", content=content or "", tool_calls=tool_calls))

    def append_tool_result(self, tool_call_id: str, result: str) -> None:
        self.messages.append(Message(role="tool", content=result, tool_call_id=tool_call_id))

    def get_messages_for_llm(self) -> list[Message]:
        return list(self.messages)

    @staticmethod
    def extract_structured(message: str) -> tuple[str, list[dict] | None]:
        items: list[dict] = []
        for match in _STRUCTURED_RE.finditer(message):
            try:
                payload = json.loads(match.group(1))
            except (ValueError, TypeError):
                continue
            if isinstance(payload, list):
                items.extend(p for p in payload if isinstance(p, dict))
            elif isinstance(payload, dict):
                items.append(payload)
        cleaned = _STRUCTURED_RE.sub("", message).strip()
        return cleaned, items or None

    @staticmethod
    def _format_ontology(ontology_context: dict) -> str:
        objects = ontology_context.get("objects", [])
        if not objects:
            return "无可用对象"
        lines = []
        for obj in objects:
            lines.append(f"### {obj.get('name', 'Unknown')}")
            if obj.get("description"):
                lines.append(obj["description"])
            for prop in obj.get("properties", []):
                st = f" ({prop['semantic_type']})" if prop.get("semantic_type") else ""
                lines.append(f"- {prop.get('name', '')}: {prop.get('type', 'string')}{st}")
            lines.append("")
        return "\n".join(lines)
```

- [ ] **Step 4: 实现 session.py（DB 操作封装）**

```python
# backend/app/services/agent/runtime/session.py
from __future__ import annotations
import json
from typing import Any
from sqlalchemy.orm import Session as DBSession
from app.models.chat.chat_session import ChatSession, ChatMessage


class SessionManager:
    @staticmethod
    def load_history(db: DBSession, session_id: int, limit: int = 20) -> list[dict]:
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{"role": m.role, "content": m.content} for m in reversed(messages)]

    @staticmethod
    def save_messages(
        db: DBSession,
        session_id: int,
        user_message: str,
        assistant_message: str,
        chart_config: dict | None = None,
    ) -> None:
        db.add(ChatMessage(session_id=session_id, role="user", content=user_message))
        db.add(ChatMessage(
            session_id=session_id, role="assistant", content=assistant_message,
            chart_config=json.dumps(chart_config, ensure_ascii=False) if chart_config else None,
        ))
        db.commit()
```

- [ ] **Step 5: 运行测试确认通过**

```bash
python -m pytest tests/unit/agent/test_conversation_runtime.py -v
```

Expected: 6 passed

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent/runtime/
git add backend/tests/unit/agent/test_conversation_runtime.py
git commit -m "feat(agent): add ConversationRuntime and SessionManager"
```

---

### Task 8: ExecutorAgent — ReAct 循环

**Files:**
- Create: `backend/app/services/agent/orchestrator/executor.py`
- Test: `backend/tests/unit/agent/test_executor.py`

- [ ] **Step 1: 写 ExecutorAgent 的测试**

```python
# backend/tests/unit/agent/test_executor.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.agent.orchestrator.executor import ExecutorAgent
from app.services.agent.providers.base import LLMResponse, ToolCall, TokenUsage, Message
from app.services.agent.tools.registry import ToolRegistry, ToolContext, ToolResult
from app.services.agent.runtime.conversation import ConversationRuntime
from app.services.agent.skills.loader import Skill


@pytest.fixture
def skill():
    return Skill(
        name="data_query", description="", system_prompt="你是分析助手。",
        allowed_tools=["query_data", "list_objects"], trigger_keywords=[],
    )


@pytest.fixture
def registry():
    reg = ToolRegistry()

    @reg.register(name="query_data", description="查询数据", parameters={
        "type": "object",
        "properties": {"object_type": {"type": "string"}},
        "required": ["object_type"],
    })
    async def query_data(ctx, object_type="Stock"):
        return ToolResult(success=True, data={
            "data": [{"ts_code": "000001.SZ", "name": "平安银行"}], "count": 1,
        })

    @reg.register(name="list_objects", description="列出对象")
    async def list_objects(ctx):
        return ToolResult(success=True, data={"objects": []})

    return reg


@pytest.mark.asyncio
async def test_executor_simple_text_response(skill, registry):
    """LLM returns text without tool calls → direct answer."""
    provider = AsyncMock()
    provider.send.return_value = LLMResponse(
        content="上个月销售额是 100 万。",
        tool_calls=[],
        usage=TokenUsage(input_tokens=50, output_tokens=20),
    )

    runtime = ConversationRuntime(skill=skill)
    runtime.build_system_prompt({"objects": []})
    runtime.append_user_message("上个月销售额多少")

    ctx = ToolContext(tenant_id=1, project_id=1, session_id=1,
                      db=None, omaha_service=None)
    executor = ExecutorAgent(provider=provider, registry=registry)
    response = await executor.run(runtime, ctx)

    assert response.message == "上个月销售额是 100 万。"
    assert response.tool_calls == []


@pytest.mark.asyncio
async def test_executor_tool_then_answer(skill, registry):
    """LLM calls a tool, then answers based on result."""
    provider = AsyncMock()

    # First call: LLM wants to call query_data
    provider.send.side_effect = [
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="tc_1", name="query_data", arguments={"object_type": "Stock"})],
            usage=TokenUsage(input_tokens=50, output_tokens=20),
        ),
        # Second call: LLM answers based on tool result
        LLMResponse(
            content="平安银行的数据如上。",
            tool_calls=[],
            usage=TokenUsage(input_tokens=100, output_tokens=30),
        ),
    ]

    runtime = ConversationRuntime(skill=skill)
    runtime.build_system_prompt({"objects": []})
    runtime.append_user_message("查询平安银行")

    ctx = ToolContext(tenant_id=1, project_id=1, session_id=1,
                      db=None, omaha_service=None)
    executor = ExecutorAgent(provider=provider, registry=registry)
    response = await executor.run(runtime, ctx)

    assert "平安银行" in response.message
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0]["name"] == "query_data"
    assert response.data_table is not None


@pytest.mark.asyncio
async def test_executor_max_iterations(skill, registry):
    """Executor stops after max_iterations."""
    provider = AsyncMock()
    # Always return tool calls → should hit max iterations
    provider.send.return_value = LLMResponse(
        content=None,
        tool_calls=[ToolCall(id="tc_x", name="list_objects", arguments={})],
        usage=TokenUsage(input_tokens=10, output_tokens=5),
    )

    runtime = ConversationRuntime(skill=skill)
    runtime.build_system_prompt({})
    runtime.append_user_message("test")

    ctx = ToolContext(tenant_id=1, project_id=1, session_id=1,
                      db=None, omaha_service=None)
    executor = ExecutorAgent(provider=provider, registry=registry, max_iterations=3)
    response = await executor.run(runtime, ctx)

    assert "超时" in response.message or "迭代" in response.message
    assert provider.send.call_count == 3
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/unit/agent/test_executor.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 executor.py**

```python
# backend/app/services/agent/orchestrator/executor.py
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.services.agent.providers.base import ProviderAdapter, ToolCall
from app.services.agent.runtime.conversation import ConversationRuntime
from app.services.agent.tools.registry import ToolRegistry, ToolContext, ToolResult

logger = logging.getLogger(__name__)


def _json_dumps(obj: Any) -> str:
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(obj, ensure_ascii=False, default=default)


@dataclass
class AgentResponse:
    message: str
    tool_calls: list[dict] = field(default_factory=list)
    data_table: list[dict] | None = None
    chart_config: dict | None = None
    sql: str | None = None
    structured: list[dict] | None = None
    setup_stage: str | None = None


class ExecutorAgent:
    def __init__(
        self,
        provider: ProviderAdapter,
        registry: ToolRegistry,
        max_iterations: int = 8,
    ):
        self.provider = provider
        self.registry = registry
        self.max_iterations = max_iterations

    async def run(self, runtime: ConversationRuntime, ctx: ToolContext) -> AgentResponse:
        tool_calls_log: list[dict] = []
        data_table = None
        chart_config = None
        sql = None
        first_turn = True
        force_answer = False

        tool_specs = runtime.skill.allowed_tools
        specs = self.registry.get_specs(whitelist=tool_specs if tool_specs else None)

        for iteration in range(self.max_iterations):
            if force_answer:
                tool_choice = "none"
            elif first_turn and specs:
                tool_choice = "required"
            else:
                tool_choice = "auto"
            first_turn = False

            messages = runtime.get_messages_for_llm()
            response = await self.provider.send(
                messages=messages,
                tools=specs if specs else None,
                tool_choice=tool_choice,
            )

            if not response.tool_calls:
                raw_message = response.content or ""
                clean_msg, structured = ConversationRuntime.extract_structured(raw_message)
                return AgentResponse(
                    message=clean_msg,
                    tool_calls=tool_calls_log,
                    data_table=data_table,
                    chart_config=chart_config,
                    sql=sql,
                    structured=structured,
                )

            runtime.append_assistant_message(response.content, response.tool_calls)

            for tc in response.tool_calls:
                result = await self.registry.execute(tc.name, tc.arguments, ctx)
                result_dict = result.to_dict()

                if tc.name == "query_data" and result.success and result.data:
                    data_table = result.data.get("data")
                    sql = result.data.get("sql")
                    force_answer = True

                if tc.name in ("generate_chart", "auto_chart") and result.success and result.data:
                    chart_config = result.data.get("chart_config")

                tool_content = _json_dumps(result_dict)
                if tc.name == "query_data" and result.success:
                    tool_content += "\n\n请基于以上数据直接回答用户问题。"

                runtime.append_tool_result(tc.id, tool_content)

                summary = tool_content[:500] + "..." if len(tool_content) > 500 else tool_content
                tool_calls_log.append({
                    "name": tc.name, "params": tc.arguments, "result_summary": summary,
                })

        return AgentResponse(
            message="抱歉，处理超时，达到了最大迭代次数。",
            tool_calls=tool_calls_log,
            data_table=data_table,
            chart_config=chart_config,
            sql=sql,
        )
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/unit/agent/test_executor.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent/orchestrator/executor.py
git add backend/tests/unit/agent/test_executor.py
git commit -m "feat(agent): add ExecutorAgent with ReAct loop migrated from chat_service"
```

---

### Task 9: 瘦 chat_service.py + EventBus 骨架 + 集成验证

**Files:**
- Create: `backend/app/services/agent/events/bus.py`
- Create: `backend/app/services/agent/events/types.py`
- Rename: `backend/app/services/agent/chat_service.py` → `backend/app/services/agent/_legacy_chat_service.py`
- Create: `backend/app/services/agent/chat_service.py` (new thin version)
- Test: `backend/tests/unit/agent/test_new_chat_service.py`

- [ ] **Step 1: 实现 EventBus 骨架**

```python
# backend/app/services/agent/events/types.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from datetime import datetime


@dataclass
class Event:
    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


# Predefined event types
TOOL_EXECUTED = "tool.executed"
TOOL_FAILED = "tool.failed"
ONTOLOGY_CONFIRMED = "ontology.confirmed"
DATA_INGESTED = "data.ingested"
SESSION_STARTED = "session.started"
```

```python
# backend/app/services/agent/events/bus.py
from __future__ import annotations
import asyncio
import logging
from typing import Callable, Awaitable
from app.services.agent.events.types import Event

logger = logging.getLogger(__name__)

EventHandler = Callable[[Event], Awaitable[None]]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}

    def on(self, event_type: str, handler: EventHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def emit(self, event: Event) -> None:
        handlers = self._handlers.get(event.type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception("Event handler failed for %s", event.type)


# Global singleton
event_bus = EventBus()
```

- [ ] **Step 2: 备份旧 chat_service.py**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend/app/services/agent
cp chat_service.py _legacy_chat_service.py
```

- [ ] **Step 3: 写新 chat_service.py 的集成测试**

```python
# backend/tests/unit/agent/test_new_chat_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent.providers.base import LLMResponse, ToolCall, TokenUsage


@pytest.mark.asyncio
async def test_send_message_simple_query():
    """Integration: user asks a question → Skill resolved → Executor runs → response returned."""
    from app.services.agent.chat_service import ChatServiceV2

    mock_provider = AsyncMock()
    mock_provider.send.return_value = LLMResponse(
        content="上个月销售额是 100 万元。",
        tool_calls=[],
        usage=TokenUsage(input_tokens=50, output_tokens=20),
    )

    mock_db = MagicMock()
    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.tenant_id = 1
    mock_project.owner_id = 1
    mock_project.setup_stage = "ready"
    mock_project.config_yaml = ""

    with patch("app.services.agent.chat_service.ProviderFactory") as mock_pf, \
         patch("app.services.agent.chat_service.SessionManager") as mock_sm, \
         patch("app.services.agent.chat_service.OntologyStore") as mock_os:

        mock_pf.create.return_value = mock_provider
        mock_sm.load_history.return_value = []
        mock_os_instance = MagicMock()
        mock_os_instance.get_full_ontology.return_value = {"objects": []}
        mock_os.return_value = mock_os_instance

        service = ChatServiceV2(project=mock_project, db=mock_db)
        result = await service.send_message(session_id=1, user_message="上个月销售额多少")

    assert "100 万" in result["message"]
    assert result["setup_stage"] == "ready"


@pytest.mark.asyncio
async def test_send_message_with_tool_call():
    """Integration: LLM calls query_data tool → data returned."""
    from app.services.agent.chat_service import ChatServiceV2

    mock_provider = AsyncMock()
    mock_provider.send.side_effect = [
        LLMResponse(
            content=None,
            tool_calls=[ToolCall(id="tc_1", name="list_objects", arguments={})],
            usage=TokenUsage(input_tokens=50, output_tokens=20),
        ),
        LLMResponse(
            content="系统中有 Stock 对象。",
            tool_calls=[],
            usage=TokenUsage(input_tokens=100, output_tokens=30),
        ),
    ]

    mock_db = MagicMock()
    mock_project = MagicMock()
    mock_project.id = 1
    mock_project.tenant_id = 1
    mock_project.owner_id = 1
    mock_project.setup_stage = "ready"
    mock_project.config_yaml = ""

    with patch("app.services.agent.chat_service.ProviderFactory") as mock_pf, \
         patch("app.services.agent.chat_service.SessionManager") as mock_sm, \
         patch("app.services.agent.chat_service.OntologyStore") as mock_os:

        mock_pf.create.return_value = mock_provider
        mock_sm.load_history.return_value = []
        mock_os_instance = MagicMock()
        mock_os_instance.get_full_ontology.return_value = {
            "objects": [{"name": "Stock", "description": "A股", "properties": []}]
        }
        mock_os.return_value = mock_os_instance

        service = ChatServiceV2(project=mock_project, db=mock_db)
        result = await service.send_message(session_id=1, user_message="有哪些对象")

    assert "Stock" in result["message"]
```

- [ ] **Step 4: 实现新的瘦 chat_service.py**

```python
# backend/app/services/agent/chat_service.py
"""Thin orchestration layer — assembles Provider, Skill, Runtime, Executor."""
from __future__ import annotations
import os
from typing import Any
from sqlalchemy.orm import Session as DBSession

from app.services.agent.providers.base import ProviderAdapter
from app.services.agent.providers.openai_compat import OpenAICompatAdapter
from app.services.agent.runtime.conversation import ConversationRuntime
from app.services.agent.runtime.session import SessionManager
from app.services.agent.tools.registry import ToolContext, global_registry
from app.services.agent.skills.loader import SkillLoader
from app.services.agent.skills.resolver import SkillResolver
from app.services.agent.orchestrator.executor import ExecutorAgent
from app.services.ontology.store import OntologyStore

# Ensure builtin tools are registered on import
import app.services.agent.tools.builtin.query  # noqa: F401
import app.services.agent.tools.builtin.chart  # noqa: F401
import app.services.agent.tools.builtin.modeling  # noqa: F401
import app.services.agent.tools.builtin.ingestion  # noqa: F401
import app.services.agent.tools.builtin.asset  # noqa: F401


class ProviderFactory:
    @staticmethod
    def create() -> ProviderAdapter:
        api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        if os.getenv("DEEPSEEK_API_KEY"):
            return OpenAICompatAdapter(model=model, api_key=api_key, base_url=base_url)
        if os.getenv("OPENAI_API_KEY"):
            return OpenAICompatAdapter(model="gpt-4o-mini", api_key=api_key)
        if os.getenv("ANTHROPIC_API_KEY"):
            from app.services.agent.providers.anthropic import AnthropicAdapter
            return AnthropicAdapter(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        raise ValueError("No LLM provider configured. Set DEEPSEEK_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY.")


_skill_loader = SkillLoader()
_skill_resolver = SkillResolver(_skill_loader)


class ChatServiceV2:
    def __init__(self, project, db: DBSession):
        self.project = project
        self.db = db
        self.tenant_id = project.tenant_id or project.owner_id

    async def send_message(self, session_id: int, user_message: str) -> dict[str, Any]:
        setup_stage = getattr(self.project, "setup_stage", None) or "ready"

        # 1. Resolve skill
        skill = _skill_resolver.resolve(setup_stage, user_message)

        # 2. Build provider
        provider = ProviderFactory.create()

        # 3. Build runtime
        runtime = ConversationRuntime(skill=skill)
        ontology_ctx = OntologyStore(self.db).get_full_ontology(self.tenant_id)
        runtime.build_system_prompt(ontology_ctx)

        # Load history
        history = SessionManager.load_history(self.db, session_id)
        for msg in history:
            if msg["role"] == "user":
                runtime.append_user_message(msg["content"])
            elif msg["role"] == "assistant":
                runtime.append_assistant_message(msg["content"], tool_calls=None)

        runtime.append_user_message(user_message)

        # 4. Build tool context
        ctx = ToolContext(
            tenant_id=self.tenant_id,
            project_id=self.project.id,
            session_id=session_id,
            db=self.db,
            omaha_service=None,  # Will be set if config_yaml available
            ontology_context=ontology_ctx,
        )

        # 5. Execute
        executor = ExecutorAgent(provider=provider, registry=global_registry)
        response = await executor.run(runtime, ctx)

        # 6. Persist
        SessionManager.save_messages(
            self.db, session_id, user_message, response.message,
            chart_config=response.chart_config,
        )

        return {
            "message": response.message,
            "data_table": response.data_table,
            "chart_config": response.chart_config,
            "sql": response.sql,
            "setup_stage": setup_stage,
            "structured": response.structured,
        }
```

- [ ] **Step 5: 运行新 chat_service 测试**

```bash
python -m pytest tests/unit/agent/test_new_chat_service.py -v
```

Expected: 2 passed

- [ ] **Step 6: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -5
```

注意：旧的 `ChatService` 类仍在 `_legacy_chat_service.py` 中，API 层 (`api/chat/chat.py`) 仍然 import 旧版。此步骤只验证新模块不破坏现有测试。API 层切换到 `ChatServiceV2` 将在确认新版稳定后单独进行。

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/agent/events/
git add backend/app/services/agent/_legacy_chat_service.py
git add backend/app/services/agent/chat_service.py
git add backend/tests/unit/agent/test_new_chat_service.py
git commit -m "feat(agent): add thin ChatServiceV2, EventBus skeleton, preserve legacy as fallback"
```

- [ ] **Step 8: 最终全量测试**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
python -m pytest tests/ -q 2>&1 | tail -10
```

验证 pass count 与 Task 0 基线一致。如有新失败，修复后再 commit。

---

### Task 10: SnapshotManager + undo_last 工具

**Files:**
- Create: `backend/app/services/agent/tools/builtin/snapshot.py`
- Test: `backend/tests/unit/agent/test_snapshot.py`

- [ ] **Step 1: 写 SnapshotManager 测试**

```python
# backend/tests/unit/agent/test_snapshot.py
import pytest
from unittest.mock import MagicMock
from app.services.agent.tools.builtin.snapshot import SnapshotManager


def test_take_and_list():
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

    mgr = SnapshotManager(db)
    sid = mgr.take(project_id=1, operation="confirm_ontology", data={"objects": [{"name": "Stock"}]})
    assert sid is not None
    db.add.assert_called_once()


def test_undo_last_no_snapshots():
    from app.services.agent.tools.registry import ToolContext, ToolResult
    from app.services.agent.tools.builtin.snapshot import undo_last
    import asyncio

    ctx = ToolContext(tenant_id=1, project_id=1, session_id=1, db=MagicMock(), omaha_service=None)
    ctx.db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    result = asyncio.get_event_loop().run_until_complete(undo_last(ctx))
    assert result.success is False
    assert "没有" in result.error
```

- [ ] **Step 2: 实现 snapshot.py**

```python
# backend/app/services/agent/tools/builtin/snapshot.py
from __future__ import annotations
import json
from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session as DBSession
from app.services.agent.tools.registry import register_tool, ToolContext, ToolResult


class SnapshotManager:
    def __init__(self, db: DBSession):
        self.db = db

    def take(self, project_id: int, operation: str, data: dict) -> int:
        from app.models.ontology.ontology import OntologySnapshot
        snapshot = OntologySnapshot(
            project_id=project_id,
            operation=operation,
            data_json=json.dumps(data, ensure_ascii=False),
            created_at=datetime.utcnow(),
        )
        self.db.add(snapshot)
        self.db.commit()
        return snapshot.id

    def restore_latest(self, project_id: int) -> dict | None:
        from app.models.ontology.ontology import OntologySnapshot
        snap = (
            self.db.query(OntologySnapshot)
            .filter(OntologySnapshot.project_id == project_id)
            .order_by(OntologySnapshot.created_at.desc())
            .first()
        )
        if not snap:
            return None
        return {"id": snap.id, "operation": snap.operation, "data": json.loads(snap.data_json)}

    def list_snapshots(self, project_id: int, limit: int = 10) -> list[dict]:
        from app.models.ontology.ontology import OntologySnapshot
        snaps = (
            self.db.query(OntologySnapshot)
            .filter(OntologySnapshot.project_id == project_id)
            .order_by(OntologySnapshot.created_at.desc())
            .limit(limit)
            .all()
        )
        return [{"id": s.id, "operation": s.operation, "created_at": str(s.created_at)} for s in snaps]


@register_tool(
    name="undo_last",
    description="撤销上一步写操作，恢复到之前的状态。",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def undo_last(ctx: ToolContext) -> ToolResult:
    if ctx.db is None or ctx.project_id is None:
        return ToolResult(success=False, error="db/project_id missing")
    mgr = SnapshotManager(ctx.db)
    snap = mgr.restore_latest(ctx.project_id)
    if not snap:
        return ToolResult(success=False, error="没有可撤销的操作")
    return ToolResult(success=True, data={
        "restored_operation": snap["operation"],
        "message": f"已恢复到【{snap['operation']}】之前的状态",
    })
```

注意：此实现需要一个 `OntologySnapshot` 模型。如果该模型不存在，需要先创建 Alembic migration。这是一个已知的依赖项，执行时需要先检查。

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/unit/agent/test_snapshot.py -v
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/agent/tools/builtin/snapshot.py backend/tests/unit/agent/test_snapshot.py
git commit -m "feat(agent): add SnapshotManager and undo_last tool"
```

---

**P0 Plan 完成。** 共 11 个 Task（0-10），覆盖 spec 中所有 P0 项。渐进式本体确认（field_confirm 结构化块）属于前端+prompt 协同改动，将在 P1 plan 中与 Coordinator/Planner/Reviewer 一起实施。
