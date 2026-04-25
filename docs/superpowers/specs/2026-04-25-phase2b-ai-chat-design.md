# Phase 2b: AI对话主界面 — 设计文档

## 1. 目标

将AgentService从占位符升级为真正的AI对话引擎 — 接入LLM（Deepseek/OpenAI/Anthropic），实现ReAct工具调用循环，让用户可以用自然语言查询业务数据、生成图表。

**范围：** 纯后端重构。前端零改动，返回格式向后兼容。

**策略：** 从现有ChatService（587行，已有完整LLM调用能力）迁移核心逻辑到AgentService，ChatService瘦身为会话管理层。

## 2. 重构策略

```
现状：
  ChatService = system prompt + LLM调用 + ReAct循环 + 工具执行 + 图表 + 会话管理
  AgentService = ontology上下文 + 占位符响应

目标：
  AgentService = ontology上下文 + LLM调用 + ReAct循环 + 工具执行 + 图表
  ChatService = 会话管理 + 消息持久化 + 委托AgentService
```

迁移内容：
- `_call_openai_compatible()` ReAct循环
- `_call_deepseek()` / `_call_anthropic()` provider适配
- tool calling执行逻辑
- 图表生成逻辑（作为AgentToolkit的generate_chart工具）

不迁移：
- 会话CRUD（留在ChatService）
- 消息持久化（留在ChatService）
- 金融专属system prompt（替换为ontology-driven通用prompt）

## 3. AgentService升级

### 3.1 新增chat()方法

```python
class AgentService:
    def __init__(self, ontology_context, toolkit, provider="deepseek"):
        self.ontology_context = ontology_context
        self.toolkit = toolkit
        self.provider = provider

    def chat(self, message: str, history: list[dict] = None) -> AgentResponse:
        system_prompt = self.build_system_prompt()
        tools_schema = self._build_tools_schema()

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages += history
        messages.append({"role": "user", "content": message})

        return self._react_loop(messages, tools_schema)
```

### 3.2 ReAct循环（从ChatService迁移）

```python
def _react_loop(self, messages, tools_schema, max_iterations=8):
    tool_calls_log = []
    data_table = None
    chart_config = None
    sql = None

    for i in range(max_iterations):
        response = self._call_llm(messages, tools_schema)

        if not response.tool_calls:
            return AgentResponse(
                text=response.content,
                tool_calls=tool_calls_log,
                data_table=data_table,
                chart_config=chart_config,
                sql=sql,
            )

        for tool_call in response.tool_calls:
            name, params = self.parse_tool_call(tool_call)
            result = self.toolkit.execute_tool(name, params)
            tool_calls_log.append({"tool": name, "params": params, "result_summary": "..."})

            if name == "query_data" and result.get("success"):
                data_table = result.get("data")
                sql = result.get("sql")
            if name == "generate_chart" and result.get("success"):
                chart_config = result.get("chart_config")

            messages.append({"role": "assistant", "tool_calls": [tool_call]})
            messages.append({"role": "tool", "content": self.format_tool_result(name, result)})

    return AgentResponse(text="分析完成，但达到了最大迭代次数。", ...)
```

### 3.3 LLM调用（多provider支持）

```python
def _call_llm(self, messages, tools_schema):
    if self.provider == "deepseek":
        client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL)
        model = settings.DEEPSEEK_MODEL
    elif self.provider == "openai":
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        model = "gpt-4o-mini"
    elif self.provider == "anthropic":
        # Anthropic用不同的SDK，需要适配
        return self._call_anthropic(messages, tools_schema)

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools_schema,
        temperature=0.1,
    )
    return response.choices[0].message
```

### 3.4 工具Schema转换

将AgentToolkit的自定义格式转换为OpenAI function calling格式：

```python
def _build_tools_schema(self) -> list[dict]:
    tools = []
    for tool_def in self.toolkit.get_tool_definitions():
        properties = {}
        required = []
        for pname, pdef in tool_def.get("parameters", {}).items():
            properties[pname] = {"type": pdef["type"], "description": pdef.get("description", "")}
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

## 4. AgentToolkit扩展

新增generate_chart工具：

```python
def _generate_chart(self, params: dict) -> dict:
    """根据数据和用户意图生成ECharts配置。"""
    data = params.get("data", [])
    chart_type = params.get("chart_type", "bar")
    title = params.get("title", "")
    x_field = params.get("x_field")
    y_field = params.get("y_field")

    # 生成ECharts option
    chart_config = {
        "title": {"text": title},
        "xAxis": {"type": "category", "data": [row.get(x_field, "") for row in data]},
        "yAxis": {"type": "value"},
        "series": [{"type": chart_type, "data": [row.get(y_field, 0) for row in data]}],
    }
    return {"success": True, "chart_config": chart_config}
```

完整工具集：query_data, list_objects, get_schema, generate_chart

## 5. ChatService瘦身

`send_message()` 改造：

```python
def send_message(self, project_id, session_id, message):
    # 1. 加载历史消息
    history = self._load_history(session_id, limit=20)

    # 2. 构建AgentService
    store = OntologyStore(self.db)
    tenant_id = self._get_tenant_id(project_id)
    ontology_context = store.get_full_ontology(tenant_id)
    omaha_service = OmahaService(self._get_config(project_id))
    toolkit = AgentToolkit(omaha_service=omaha_service)
    agent = AgentService(ontology_context=ontology_context, toolkit=toolkit)

    # 3. 调用Agent
    response = agent.chat(message, history)

    # 4. 保存消息到DB
    self._save_message(session_id, "user", message)
    self._save_message(session_id, "assistant", response.text,
                       data_table=response.data_table,
                       chart_config=response.chart_config,
                       sql=response.sql)

    return response
```

## 6. API端点适配

```
POST /api/v1/chat/{project_id}/sessions/{session_id}/message
  → ChatService.send_message() → AgentService.chat()
  返回: {message, data_table, chart_config, sql}  ← 格式不变

POST /api/v1/agent/{project_id}/chat
  → AgentService.chat()（无会话持久化）
  返回: AgentChatResponse  ← 扩展字段
```

## 7. 响应格式

```python
class AgentChatResponse(BaseModel):
    response: str
    tool_calls: list[ToolCallRecord] = []
    data_table: list[dict] | None = None
    chart_config: dict | None = None
    sql: str | None = None
    sources: list[str] = []
```

向后兼容：现有前端读取的字段（message, data_table, chart_config, sql）全部保留。

## 8. 文件结构

### 修改
- `backend/app/services/agent.py` — 添加chat(), _react_loop(), _call_llm(), _build_tools_schema()
- `backend/app/services/agent_tools.py` — 添加generate_chart工具
- `backend/app/services/chat.py` — 瘦身send_message()，委托AgentService
- `backend/app/api/agent.py` — 替换占位符为AgentService.chat()
- `backend/app/schemas/agent.py` — 扩展AgentChatResponse

### 新建
- `backend/tests/test_agent_llm.py` — ReAct循环测试（mock LLM）
- `backend/tests/test_agent_chart.py` — generate_chart工具测试
- `backend/tests/test_chat_refactor.py` — ChatService委托回归测试

## 9. 测试策略

- **test_agent_llm.py** — mock OpenAI client，验证：
  - 单轮对话（无tool call，直接返回文本）
  - ReAct循环（tool call → execute → 继续 → 最终文本）
  - 多工具连续调用
  - max_iterations退出
  - 工具执行失败时的错误处理
  - 多provider切换（deepseek/openai）
- **test_agent_chart.py** — 验证generate_chart输出合法ECharts配置
- **test_chat_refactor.py** — 验证send_message正确委托AgentService，消息正确持久化

不测真实LLM。全部mock。

## 10. 配置

复用现有config.py的LLM设置，不新增配置项：
- `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

AgentService通过`settings.DEEPSEEK_API_KEY`是否存在来自动选择provider。
