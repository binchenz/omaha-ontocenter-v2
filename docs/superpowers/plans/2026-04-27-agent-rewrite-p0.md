# Agent 内核重写 P0 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 2160 行单体 agent 重构为分层架构：Provider 抽象 → ToolRegistry → Skills → ConversationRuntime → ExecutorAgent → 瘦 chat_service.py，保持前端 API 兼容。

**Architecture:** 借鉴 claw-code 的多 crate 分层，映射到 Python 模块。工具通过装饰器自注册到 ToolRegistry，Skill 以 YAML 定义 prompt + 工具白名单，ConversationRuntime 管理会话状态，ExecutorAgent 运行 ReAct 循环。现有工具业务逻辑直接迁移，不重写。

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Pydantic v2, PyYAML, openai SDK, anthropic SDK

**Spec:** `docs/superpowers/specs/2026-04-27-agent-rewrite-design.md`

**Python:** `/Users/wangfushuaiqi/omaha_ontocenter/backend/venv311/bin/python`

**Test baseline:** Run `cd backend && python -m pytest tests/ -x -q` before starting. Record pass count. Zero new regression allowed.

---

### Task 0: 准备工作 — 建立测试基线

**Files:**
- None (read-only)

- [ ] **Step 1: 运行现有测试，记录基线**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
python -m pytest tests/ -x -q 2>&1 | tail -5
```

Record the pass/fail counts. All subsequent tasks must maintain this baseline.

- [ ] **Step 2: 创建新目录结构**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend/app/services/agent
mkdir -p providers runtime tools/builtin skills/definitions orchestrator events/handlers
touch providers/__init__.py runtime/__init__.py tools/__init__.py tools/builtin/__init__.py
touch skills/__init__.py orchestrator/__init__.py events/__init__.py events/handlers/__init__.py
```

- [ ] **Step 3: Commit**

```bash
git add -A backend/app/services/agent/
git commit -m "chore: scaffold agent rewrite directory structure"
```

---

### Task 1: Provider 抽象层 — 基础类型 + OpenAI 兼容适配器

**Files:**
- Create: `backend/app/services/agent/providers/base.py`
- Create: `backend/app/services/agent/providers/openai_compat.py`
- Test: `backend/tests/unit/agent/test_providers.py`

- [ ] **Step 1: 写 base.py 的失败测试**

```python
# backend/tests/unit/agent/test_providers.py
import pytest
from app.services.agent.providers.base import (
    ToolCall, TokenUsage, LLMResponse, Message, ToolSpec, ProviderAdapter
)


def test_tool_call_creation():
    tc = ToolCall(id="tc_1", name="query_data", arguments={"object_type": "Stock"})
    assert tc.id == "tc_1"
    assert tc.name == "query_data"
    assert tc.arguments == {"object_type": "Stock"}


def test_llm_response_creation():
    resp = LLMResponse(
        content="hello",
        tool_calls=[],
        usage=TokenUsage(input_tokens=10, output_tokens=5),
    )
    assert resp.content == "hello"
    assert resp.tool_calls == []
    assert resp.usage.input_tokens == 10


def test_provider_adapter_is_abstract():
    with pytest.raises(TypeError):
        ProviderAdapter(model="test", api_key="key")
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
python -m pytest tests/unit/agent/test_providers.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 base.py**

```python
# backend/app/services/agent/providers/base.py
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall]
    usage: TokenUsage


@dataclass
class Message:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any] = field(default_factory=dict)


class ProviderAdapter(ABC):
    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def send(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse: ...
```

- [ ] **Step 4: 运行测试确认通过**

```bash
python -m pytest tests/unit/agent/test_providers.py -v
```

Expected: 3 passed

- [ ] **Step 5: 写 OpenAICompatAdapter 的测试**

在 `test_providers.py` 末尾追加：

```python
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent.providers.openai_compat import OpenAICompatAdapter


@pytest.mark.asyncio
async def test_openai_compat_send_no_tools():
    adapter = OpenAICompatAdapter(model="deepseek-chat", api_key="fake")

    mock_choice = MagicMock()
    mock_choice.message.content = "Hello"
    mock_choice.message.tool_calls = None
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5

    with patch.object(adapter, "_client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = await adapter.send([Message(role="user", content="hi")])

    assert result.content == "Hello"
    assert result.tool_calls == []
    assert result.usage.input_tokens == 10


@pytest.mark.asyncio
async def test_openai_compat_send_with_tool_calls():
    adapter = OpenAICompatAdapter(model="deepseek-chat", api_key="fake")

    mock_tc = MagicMock()
    mock_tc.id = "tc_1"
    mock_tc.function.name = "query_data"
    mock_tc.function.arguments = '{"object_type": "Stock"}'

    mock_choice = MagicMock()
    mock_choice.message.content = None
    mock_choice.message.tool_calls = [mock_tc]
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage.prompt_tokens = 20
    mock_response.usage.completion_tokens = 10

    with patch.object(adapter, "_client") as mock_client:
        mock_client.chat.completions.create.return_value = mock_response
        result = await adapter.send(
            [Message(role="user", content="查询")],
            tools=[ToolSpec(name="query_data", description="查询", parameters={})],
        )

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "query_data"
    assert result.tool_calls[0].arguments == {"object_type": "Stock"}
```

- [ ] **Step 6: 实现 OpenAICompatAdapter**

```python
# backend/app/services/agent/providers/openai_compat.py
from __future__ import annotations
import json
from typing import Any

from app.services.agent.providers.base import (
    ProviderAdapter, Message, ToolSpec, LLMResponse, ToolCall, TokenUsage,
)

try:
    import openai
except ImportError:
    openai = None


class OpenAICompatAdapter(ProviderAdapter):
    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        super().__init__(model=model, api_key=api_key, base_url=base_url)
        if openai is None:
            raise ImportError("openai package not installed")
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)

    async def send(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        oai_messages = self._convert_messages(messages)
        kwargs: dict[str, Any] = {"model": self.model, "messages": oai_messages}
        if tools:
            kwargs["tools"] = [self._convert_tool(t) for t in tools]
            kwargs["tool_choice"] = tool_choice
        response = self._client.chat.completions.create(**kwargs)
        return self._parse_response(response)

    @staticmethod
    def _convert_messages(messages: list[Message]) -> list[dict]:
        result = []
        for m in messages:
            msg: dict[str, Any] = {"role": m.role, "content": m.content or ""}
            if m.tool_calls:
                msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments, ensure_ascii=False)},
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            result.append(msg)
        return result

    @staticmethod
    def _convert_tool(spec: ToolSpec) -> dict:
        return {
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": spec.parameters,
            },
        }

    @staticmethod
    def _parse_response(response) -> LLMResponse:
        choice = response.choices[0]
        tool_calls = []
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                tool_calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        return LLMResponse(
            content=choice.message.content,
            tool_calls=tool_calls,
            usage=TokenUsage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
            ),
        )
```

- [ ] **Step 7: 运行测试确认全部通过**

```bash
python -m pytest tests/unit/agent/test_providers.py -v
```

Expected: 5 passed

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/agent/providers/ backend/tests/unit/agent/test_providers.py
git commit -m "feat(agent): add Provider abstraction layer with OpenAI-compatible adapter"
```

---

### Task 2: Provider 抽象层 — Anthropic 适配器

**Files:**
- Create: `backend/app/services/agent/providers/anthropic.py`
- Modify: `backend/tests/unit/agent/test_providers.py`

- [ ] **Step 1: 写 AnthropicAdapter 的测试**

在 `test_providers.py` 末尾追加：

```python
from app.services.agent.providers.anthropic import AnthropicAdapter


@pytest.mark.asyncio
async def test_anthropic_send_text_only():
    adapter = AnthropicAdapter(model="claude-sonnet-4-20250514", api_key="fake")

    mock_text = MagicMock()
    mock_text.type = "text"
    mock_text.text = "Hello from Claude"
    mock_response = MagicMock()
    mock_response.content = [mock_text]
    mock_response.usage.input_tokens = 15
    mock_response.usage.output_tokens = 8

    with patch.object(adapter, "_client") as mock_client:
        mock_client.messages.create.return_value = mock_response
        result = await adapter.send([Message(role="user", content="hi")])

    assert result.content == "Hello from Claude"
    assert result.tool_calls == []


@pytest.mark.asyncio
async def test_anthropic_send_with_tool_use():
    adapter = AnthropicAdapter(model="claude-sonnet-4-20250514", api_key="fake")

    mock_tool = MagicMock()
    mock_tool.type = "tool_use"
    mock_tool.id = "tu_1"
    mock_tool.name = "query_data"
    mock_tool.input = {"object_type": "Stock"}
    mock_response = MagicMock()
    mock_response.content = [mock_tool]
    mock_response.usage.input_tokens = 20
    mock_response.usage.output_tokens = 12

    with patch.object(adapter, "_client") as mock_client:
        mock_client.messages.create.return_value = mock_response
        result = await adapter.send(
            [Message(role="user", content="查询")],
            tools=[ToolSpec(name="query_data", description="查询", parameters={})],
        )

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "query_data"
    assert result.tool_calls[0].arguments == {"object_type": "Stock"}
```

- [ ] **Step 2: 运行测试确认失败**

```bash
python -m pytest tests/unit/agent/test_providers.py::test_anthropic_send_text_only -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 AnthropicAdapter**

```python
# backend/app/services/agent/providers/anthropic.py
from __future__ import annotations
from typing import Any

from app.services.agent.providers.base import (
    ProviderAdapter, Message, ToolSpec, LLMResponse, ToolCall, TokenUsage,
)

try:
    import anthropic
except ImportError:
    anthropic = None


class AnthropicAdapter(ProviderAdapter):
    def __init__(self, model: str, api_key: str, base_url: str | None = None):
        super().__init__(model=model, api_key=api_key, base_url=base_url)
        if anthropic is None:
            raise ImportError("anthropic package not installed")
        self._client = anthropic.Anthropic(api_key=api_key)

    async def send(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        system_msg, claude_messages = self._convert_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": claude_messages,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if tools:
            kwargs["tools"] = [self._convert_tool(t) for t in tools]
        response = self._client.messages.create(**kwargs)
        return self._parse_response(response)

    @staticmethod
    def _convert_messages(messages: list[Message]) -> tuple[str, list[dict]]:
        system_msg = ""
        claude_messages: list[dict] = []
        for m in messages:
            if m.role == "system":
                system_msg = m.content or ""
            elif m.role == "tool":
                claude_messages.append({
                    "role": "user",
                    "content": [
                        {"type": "tool_result", "tool_use_id": m.tool_call_id, "content": m.content or ""}
                    ],
                })
            elif m.role == "assistant" and m.tool_calls:
                content: list[dict] = []
                if m.content:
                    content.append({"type": "text", "text": m.content})
                for tc in m.tool_calls:
                    content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments})
                claude_messages.append({"role": "assistant", "content": content})
            else:
                claude_messages.append({"role": m.role, "content": m.content or ""})
        return system_msg, claude_messages

    @staticmethod
    def _convert_tool(spec: ToolSpec) -> dict:
        return {"name": spec.name, "description": spec.description, "input_schema": spec.parameters}

    @staticmethod
    def _parse_response(response) -> LLMResponse:
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, arguments=block.input))
        return LLMResponse(
            content=" ".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            usage=TokenUsage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
            ),
        )
```

- [ ] **Step 4: 运行测试确认全部通过**

```bash
python -m pytest tests/unit/agent/test_providers.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/agent/providers/anthropic.py backend/tests/unit/agent/test_providers.py
git commit -m "feat(agent): add Anthropic provider adapter"
```

---

### Task 3: ToolRegistry — 注册、发现、执行

**Files:**
- Create: `backend/app/services/agent/tools/registry.py`
- Test: `backend/tests/unit/agent/test_tool_registry.py`

- [ ] **Step 1: 写 ToolRegistry 的失败测试**

```python
# backend/tests/unit/agent/test_tool_registry.py
import pytest
from app.services.agent.tools.registry import (
    ToolRegistry, ToolContext, ToolResult, register_tool,
)


def test_tool_context_creation():
    ctx = ToolContext(
        tenant_id=1,
        project_id=10,
        session_id=100,
        db=None,
        omaha_service=None,
        ontology_context={"objects": []},
        uploaded_tables={},
    )
    assert ctx.tenant_id == 1
    assert ctx.project_id == 10
    assert ctx.session_id == 100


def test_tool_result_success():
    r = ToolResult(success=True, data={"count": 5})
    assert r.success is True
    assert r.data == {"count": 5}
    assert r.error is None


def test_tool_result_failure():
    r = ToolResult(success=False, error="not found")
    assert r.success is False
    assert r.error == "not found"


def test_register_and_get_specs():
    registry = ToolRegistry()

    @registry.register(
        name="test_tool",
        description="A test tool",
        parameters={
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        },
    )
    async def test_tool(ctx: ToolContext, x: str) -> ToolResult:
        return ToolResult(success=True, data={"x": x})

    specs = registry.get_specs()
    assert len(specs) == 1
    assert specs[0].name == "test_tool"
    assert specs[0].description == "A test tool"


def test_get_specs_with_whitelist():
    registry = ToolRegistry()

    @registry.register(name="tool_a", description="A")
    async def tool_a(ctx: ToolContext) -> ToolResult:
        return ToolResult(success=True)

    @registry.register(name="tool_b", description="B")
    async def tool_b(ctx: ToolContext) -> ToolResult:
        return ToolResult(success=True)

    @registry.register(name="tool_c", description="C")
    async def tool_c(ctx: ToolContext) -> ToolResult:
        return ToolResult(success=True)

    specs = registry.get_specs(whitelist=["tool_a", "tool_c"])
    names = [s.name for s in specs]
    assert names == ["tool_a", "tool_c"]


@pytest.mark.asyncio
async def test_execute_tool():
    registry = ToolRegistry()

    @registry.register(
        name="echo",
        description="Echo back",
        parameters={
            "type": "object",
            "properties": {"msg": {"type": "string"}},
            "required": ["msg"],
        },
    )
    async def echo(ctx: ToolContext, msg: str) -> ToolResult:
        return ToolResult(success=True, data={"echo": msg})

    ctx = ToolContext(
        tenant_id=1, project_id=1, session_id=1,
        db=None, omaha_service=None, ontology_context={}, uploaded_tables={},
    )
    result = await registry.execute("echo", {"msg": "hello"}, ctx)
    assert result.success is True
    assert result.data == {"echo": "hello"}


@pytest.mark.asyncio
async def test_execute_unknown_tool():
    registry = ToolRegistry()
    ctx = ToolContext(
        tenant_id=1, project_id=1, session_id=1,
        db=None, omaha_service=None, ontology_context={}, uploaded_tables={},
    )
    result = await registry.execute("nonexistent", {}, ctx)
    assert result.success is False
    assert "Unknown tool" in result.error


@pytest.mark.asyncio
async def test_execute_tool_exception():
    registry = ToolRegistry()

    @registry.register(name="bad_tool", description="Fails")
    async def bad_tool(ctx: ToolContext) -> ToolResult:
        raise ValueError("boom")

    ctx = ToolContext(
        tenant_id=1, project_id=1, session_id=1,
        db=None, omaha_service=None, ontology_context={}, uploaded_tables={},
    )
    result = await registry.execute("bad_tool", {}, ctx)
    assert result.success is False
    assert "boom" in result.error


def test_get_openai_schemas():
    registry = ToolRegistry()

    @registry.register(
        name="my_tool",
        description="Does stuff",
        parameters={
            "type": "object",
            "properties": {"q": {"type": "string", "description": "query"}},
            "required": ["q"],
        },
    )
    async def my_tool(ctx: ToolContext, q: str) -> ToolResult:
        return ToolResult(success=True)

    schemas = registry.get_openai_schemas()
    assert len(schemas) == 1
    assert schemas[0]["type"] == "function"
    assert schemas[0]["function"]["name"] == "my_tool"
    assert schemas[0]["function"]["parameters"]["properties"]["q"]["type"] == "string"


def test_global_register_tool_decorator():
    """Test the module-level register_tool that uses the global registry."""
    from app.services.agent.tools.registry import global_registry

    initial_count = len(global_registry._tools)

    @register_tool(
        name="global_test_tool",
        description="Registered globally",
    )
    async def global_test_tool(ctx: ToolContext) -> ToolResult:
        return ToolResult(success=True)

    assert len(global_registry._tools) == initial_count + 1
    specs = global_registry.get_specs(whitelist=["global_test_tool"])
    assert len(specs) == 1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
python -m pytest tests/unit/agent/test_tool_registry.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 registry.py**

```python
# backend/app/services/agent/tools/registry.py
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from app.services.agent.providers.base import ToolSpec

logger = logging.getLogger(__name__)


@dataclass
class ToolContext:
    """Dependency bag passed to every tool invocation."""
    tenant_id: int | None
    project_id: int | None
    session_id: int | None
    db: Any  # SQLAlchemy Session or None
    omaha_service: Any  # OmahaService instance or None
    ontology_context: dict = field(default_factory=dict)
    uploaded_tables: dict = field(default_factory=dict)


@dataclass
class ToolResult:
    """Uniform return type for all tools."""
    success: bool
    data: dict | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"success": self.success}
        if self.data is not None:
            d["data"] = self.data
        if self.error is not None:
            d["error"] = self.error
        return d


# Type alias for tool handler functions
ToolHandler = Callable[..., Awaitable[ToolResult]]


@dataclass
class _ToolEntry:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler


class ToolRegistry:
    """Registry for agent tools. Supports decorator-based registration."""

    def __init__(self) -> None:
        self._tools: dict[str, _ToolEntry] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict[str, Any] | None = None,
    ) -> Callable:
        """Decorator to register a tool handler.

        Usage::

            @registry.register(name="query_data", description="...", parameters={...})
            async def query_data(ctx: ToolContext, **kwargs) -> ToolResult:
                ...
        """
        if parameters is None:
            parameters = {"type": "object", "properties": {}, "required": []}

        def decorator(fn: ToolHandler) -> ToolHandler:
            self._tools[name] = _ToolEntry(
                name=name,
                description=description,
                parameters=parameters,
                handler=fn,
            )
            return fn

        return decorator

    def get_specs(self, whitelist: list[str] | None = None) -> list[ToolSpec]:
        """Return ToolSpec list, optionally filtered by whitelist."""
        entries = self._tools.values()
        if whitelist is not None:
            entries = [e for e in entries if e.name in whitelist]
            # Preserve whitelist order
            order = {n: i for i, n in enumerate(whitelist)}
            entries = sorted(entries, key=lambda e: order.get(e.name, 999))
        return [
            ToolSpec(name=e.name, description=e.description, parameters=e.parameters)
            for e in entries
        ]

    def get_openai_schemas(self, whitelist: list[str] | None = None) -> list[dict]:
        """Return tool specs in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.parameters,
                },
            }
            for spec in self.get_specs(whitelist)
        ]

    async def execute(
        self, name: str, params: dict[str, Any], ctx: ToolContext
    ) -> ToolResult:
        """Execute a registered tool by name."""
        entry = self._tools.get(name)
        if entry is None:
            return ToolResult(success=False, error=f"Unknown tool: {name}")
        try:
            result = await entry.handler(ctx, **params)
            return result
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return ToolResult(success=False, error=str(e))

    def has(self, name: str) -> bool:
        return name in self._tools

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


# ---------------------------------------------------------------------------
# Global singleton + module-level decorator
# ---------------------------------------------------------------------------
global_registry = ToolRegistry()


def register_tool(
    name: str,
    description: str,
    parameters: dict[str, Any] | None = None,
) -> Callable:
    """Module-level decorator that registers into the global registry."""
    return global_registry.register(name=name, description=description, parameters=parameters)
```

- [ ] **Step 4: 运行测试确认通过**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
python -m pytest tests/unit/agent/test_tool_registry.py -v
```

Expected: 9 passed

- [ ] **Step 5: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -5
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/agent/tools/registry.py backend/tests/unit/agent/test_tool_registry.py
git commit -m "feat(agent): add ToolRegistry with decorator registration, whitelist filtering, and async execution"
```

---

### Task 4: 内置工具迁移 — query + chart

**Files:**
- Create: `backend/app/services/agent/tools/builtin/query.py`
- Create: `backend/app/services/agent/tools/builtin/chart.py`
- Test: `backend/tests/unit/agent/test_builtin_query.py`
- Test: `backend/tests/unit/agent/test_builtin_chart.py`

- [ ] **Step 1: 写 query 工具的失败测试**

```python
# backend/tests/unit/agent/test_builtin_query.py
import pytest
from unittest.mock import MagicMock
from app.services.agent.tools.registry import ToolContext, ToolResult


@pytest.fixture
def ctx():
    mock_omaha = MagicMock()
    return ToolContext(
        tenant_id=1,
        project_id=10,
        session_id=100,
        db=None,
        omaha_service=mock_omaha,
        ontology_context={
            "objects": [
                {
                    "name": "Stock",
                    "description": "A股股票",
                    "properties": [
                        {"name": "ts_code", "type": "string"},
                        {"name": "name", "type": "string"},
                        {"name": "close", "type": "float", "semantic_type": "currency_cny"},
                    ],
                }
            ],
            "relationships": [
                {"from": "Stock", "to": "FinancialIndicator", "type": "has_many"}
            ],
        },
    )


@pytest.mark.asyncio
async def test_query_data(ctx):
    from app.services.agent.tools.builtin.query import query_data

    ctx.omaha_service.query_objects.return_value = {
        "success": True,
        "data": [{"ts_code": "000001.SZ", "name": "平安银行"}],
        "count": 1,
    }
    result = await query_data(ctx, object_type="Stock", limit=10)
    assert result.success is True
    assert result.data["data"][0]["ts_code"] == "000001.SZ"
    ctx.omaha_service.query_objects.assert_called_once()


@pytest.mark.asyncio
async def test_list_objects(ctx):
    from app.services.agent.tools.builtin.query import list_objects

    result = await list_objects(ctx)
    assert result.success is True
    assert "Stock" in [o["name"] for o in result.data["objects"]]


@pytest.mark.asyncio
async def test_get_schema_found(ctx):
    from app.services.agent.tools.builtin.query import get_schema

    result = await get_schema(ctx, object_type="Stock")
    assert result.success is True
    assert result.data["schema"]["name"] == "Stock"


@pytest.mark.asyncio
async def test_get_schema_not_found(ctx):
    from app.services.agent.tools.builtin.query import get_schema

    result = await get_schema(ctx, object_type="NonExistent")
    assert result.success is False
    assert "not found" in result.error.lower() or "未找到" in result.error


@pytest.mark.asyncio
async def test_get_relationships(ctx):
    from app.services.agent.tools.builtin.query import get_relationships

    result = await get_relationships(ctx, object_type="Stock")
    assert result.success is True
    assert len(result.data["relationships"]) == 1
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
python -m pytest tests/unit/agent/test_builtin_query.py -v
```

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 实现 query.py — 从 toolkit.py 迁移 query/list/schema**

```python
# backend/app/services/agent/tools/builtin/query.py
"""Query tools — migrated from AgentToolkit._query_data / _list_objects / _get_schema."""
from __future__ import annotations

from app.services.agent.tools.registry import (
    register_tool, ToolContext, ToolResult,
)


@register_tool(
    name="query_data",
    description="Query data from a business object. Use this to retrieve records with optional filters and column selection.",
    parameters={
        "type": "object",
        "properties": {
            "object_type": {"type": "string", "description": "Name of the object to query"},
            "columns": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Columns to return. Omit for all columns.",
            },
            "filters": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Filter conditions: [{field, operator, value}]",
            },
            "joins": {
                "type": "array",
                "items": {"type": "object"},
                "description": "JOIN 配置列表",
            },
            "limit": {"type": "integer", "description": "Max rows to return (default 100)"},
        },
        "required": ["object_type"],
    },
)
async def query_data(
    ctx: ToolContext,
    object_type: str,
    columns: list[str] | None = None,
    filters: list[dict] | None = None,
    joins: list[dict] | None = None,
    limit: int = 100,
) -> ToolResult:
    if ctx.omaha_service is None:
        return ToolResult(success=False, error="omaha_service not available")
    result = ctx.omaha_service.query_objects(
        object_type=object_type,
        selected_columns=columns,
        filters=filters,
        joins=joins,
        limit=min(limit, 100),
    )
    if not result.get("success"):
        return ToolResult(success=False, error=result.get("error", "query failed"))
    return ToolResult(success=True, data=result)


@register_tool(
    name="list_objects",
    description="List all available business objects and their descriptions.",
    parameters={"type": "object", "properties": {}, "required": []},
)
async def list_objects(ctx: ToolContext) -> ToolResult:
    objects = ctx.ontology_context.get("objects", [])
    return ToolResult(success=True, data={"objects": objects})


@register_tool(
    name="get_schema",
    description="Get the schema (fields, types, semantic types) of a business object.",
    parameters={
        "type": "object",
        "properties": {
            "object_type": {"type": "string", "description": "Name of the object"},
        },
        "required": ["object_type"],
    },
)
async def get_schema(ctx: ToolContext, object_type: str) -> ToolResult:
    for obj in ctx.ontology_context.get("objects", []):
        if obj["name"] == object_type:
            return ToolResult(success=True, data={"schema": obj})
    return ToolResult(success=False, error=f"Object '{object_type}' not found")


@register_tool(
    name="get_relationships",
    description="Get relationships for a business object.",
    parameters={
        "type": "object",
        "properties": {
            "object_type": {"type": "string", "description": "Name of the object"},
        },
        "required": ["object_type"],
    },
)
async def get_relationships(ctx: ToolContext, object_type: str) -> ToolResult:
    all_rels = ctx.ontology_context.get("relationships", [])
    obj_rels = [
        r for r in all_rels
        if r.get("from") == object_type or r.get("to") == object_type
    ]
    return ToolResult(success=True, data={"relationships": obj_rels})
```

- [ ] **Step 4: 运行 query 测试确认通过**

```bash
python -m pytest tests/unit/agent/test_builtin_query.py -v
```

Expected: 5 passed

- [ ] **Step 5: 写 chart 工具的失败测试**

```python
# backend/tests/unit/agent/test_builtin_chart.py
import pytest
from app.services.agent.tools.registry import ToolContext, ToolResult


@pytest.fixture
def ctx():
    return ToolContext(
        tenant_id=1, project_id=1, session_id=1,
        db=None, omaha_service=None, ontology_context={}, uploaded_tables={},
    )


@pytest.mark.asyncio
async def test_generate_chart_bar(ctx):
    from app.services.agent.tools.builtin.chart import generate_chart

    result = await generate_chart(
        ctx,
        data=[{"name": "A", "value": 10}, {"name": "B", "value": 20}],
        chart_type="bar",
        x_field="name",
        y_field="value",
        title="Test Bar",
    )
    assert result.success is True
    config = result.data["chart_config"]
    assert config["series"][0]["type"] == "bar"
    assert config["title"]["text"] == "Test Bar"


@pytest.mark.asyncio
async def test_generate_chart_pie(ctx):
    from app.services.agent.tools.builtin.chart import generate_chart

    result = await generate_chart(
        ctx,
        data=[{"cat": "X", "val": 60}, {"cat": "Y", "val": 40}],
        chart_type="pie",
        x_field="cat",
        y_field="val",
    )
    assert result.success is True
    config = result.data["chart_config"]
    assert config["series"][0]["type"] == "pie"
    assert len(config["series"][0]["data"]) == 2


@pytest.mark.asyncio
async def test_auto_chart_returns_config(ctx):
    from app.services.agent.tools.builtin.chart import auto_chart

    result = await auto_chart(
        ctx,
        data=[{"category": "A", "amount": 100}, {"category": "B", "amount": 200}],
    )
    assert result.success is True
    # Should auto-detect bar chart (categorical + numeric, <=10 categories)
    assert result.data["chart_config"] is not None
    assert result.data["chart_type"] == "bar"


@pytest.mark.asyncio
async def test_auto_chart_empty_data(ctx):
    from app.services.agent.tools.builtin.chart import auto_chart

    result = await auto_chart(ctx, data=[])
    assert result.success is True
    assert result.data["chart_config"] is None
```

- [ ] **Step 6: 实现 chart.py — 迁移 ChartEngine + generate_chart**

```python
# backend/app/services/agent/tools/builtin/chart.py
"""Chart tools — migrated from AgentToolkit._generate_chart + ChartEngine."""
from __future__ import annotations

from typing import Any

from app.services.agent.tools.registry import (
    register_tool, ToolContext, ToolResult,
)
from app.services.agent.chart_engine import ChartEngine

# Shared engine instance
_engine = ChartEngine()


@register_tool(
    name="generate_chart",
    description="Generate an ECharts chart config from query result data. Call this after query_data to visualize results.",
    parameters={
        "type": "object",
        "properties": {
            "data": {"type": "array", "description": "Array of data rows from query_data result"},
            "chart_type": {"type": "string", "description": "Chart type: bar, line, pie, scatter"},
            "title": {"type": "string", "description": "Chart title"},
            "x_field": {"type": "string", "description": "Field name for X axis"},
            "y_field": {"type": "string", "description": "Field name for Y axis / values"},
        },
        "required": ["data", "chart_type", "x_field", "y_field"],
    },
)
async def generate_chart(
    ctx: ToolContext,
    data: list[dict],
    chart_type: str,
    x_field: str,
    y_field: str,
    title: str = "",
) -> ToolResult:
    if not data:
        return ToolResult(success=True, data={"chart_config": None})

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
    return ToolResult(success=True, data={"chart_config": chart_config})


@register_tool(
    name="auto_chart",
    description="Automatically select chart type and build config based on data characteristics.",
    parameters={
        "type": "object",
        "properties": {
            "data": {"type": "array", "description": "Array of data rows"},
        },
        "required": ["data"],
    },
)
async def auto_chart(ctx: ToolContext, data: list[dict]) -> ToolResult:
    if not data:
        return ToolResult(success=True, data={"chart_config": None, "chart_type": None})
    chart_type = _engine.select_chart_type(data)
    chart_config = _engine.build_chart_config(data, chart_type) if chart_type else None
    return ToolResult(success=True, data={"chart_config": chart_config, "chart_type": chart_type})
```

- [ ] **Step 7: 运行 chart 测试确认通过**

```bash
python -m pytest tests/unit/agent/test_builtin_chart.py -v
```

Expected: 4 passed

- [ ] **Step 8: 运行全量测试确认无回归**

```bash
python -m pytest tests/ -x -q 2>&1 | tail -5
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/agent/tools/builtin/query.py backend/app/services/agent/tools/builtin/chart.py
git add backend/tests/unit/agent/test_builtin_query.py backend/tests/unit/agent/test_builtin_chart.py
git commit -m "feat(agent): migrate query + chart tools to ToolRegistry with @register_tool"
```

---

**续接文件（按顺序执行）：**

1. `docs/superpowers/plans/2026-04-27-agent-rewrite-p0-tasks-5-6.md` — Task 5: modeling/ingestion/asset 工具迁移, Task 6: Skill 系统
2. `docs/superpowers/plans/2026-04-27-agent-rewrite-p0-tasks-7-9.md` — Task 7: ConversationRuntime, Task 8: ExecutorAgent, Task 9: 瘦 chat_service + EventBus

