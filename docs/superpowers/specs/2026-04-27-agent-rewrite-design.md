# Agent 内核重写设计文档

> 借鉴 claw-code 三层架构（OmX/clawhip/OmO），将 OntoCenter 的 2160 行单体 agent 重构为分层、可扩展的 Agent 系统。

## 1. 现状问题

- `chat_service.py`（1083 行）：ReAct 循环、LLM 调用、工具执行、上下文组装、结构化输出解析全部耦合
- `toolkit.py`（520 行）：工具定义和实现混在一起，硬编码工具列表，无法动态注册
- `react.py`（342 行）：系统提示模板、onboarding 状态机、AgentService 类混在一个文件
- Provider 代码重复：OpenAI/DeepSeek/Anthropic 三套调用逻辑，格式转换散落各处
- 无权限控制：所有租户可调用所有工具
- 无 Skill 机制：agent 行为无法按场景定制

## 2. 目标架构

```
┌─ Skill 层 ──────────────────────────────────────┐
│  YAML 定义：prompt 片段 + 工具白名单              │
│  SkillLoader 加载 / SkillResolver 按意图匹配      │
├─ Agent 层（OmO 对应）───────────────────────────┤
│  Coordinator：意图复杂度判断                      │
│  ├─ 简单意图 → 单 Executor（ReAct 循环）          │
│  └─ 复杂意图 → Planner → Executor(s) → Reviewer  │
│  ConversationRuntime：会话状态 + 上下文组装        │
├─ 事件层（clawhip 对应）─────────────────────────┤
│  EventBus：进程内发布/订阅                        │
│  事件类型：工具执行、建模确认、健康规则触发等       │
├─ 基础设施层 ─────────────────────────────────────┤
│  ToolRegistry / PermissionEnforcer /              │
│  ProviderAdapter / SkillLoader                    │
└──────────────────────────────────────────────────┘
```

## 3. 模块设计

### 3.1 Provider 抽象层（`providers/`）

统一接口，屏蔽 OpenAI/Anthropic 格式差异。

```python
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall]  # 统一格式
    usage: TokenUsage

class ProviderAdapter(ABC):
    async def send(
        self,
        messages: list[Message],
        tools: list[ToolSpec] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse: ...
```

实现：

- `OpenAICompatAdapter`：覆盖 DeepSeek、通义千问、本地模型（任何 OpenAI 兼容 API）
- `AnthropicAdapter`：处理 Anthropic 特有的 tool_use content block 格式

配置驱动，通过 `agent_config.yaml` 或环境变量选择 provider + model：

```yaml
providers:
  default: deepseek
  deepseek:
    base_url: ${DEEPSEEK_BASE_URL}
    api_key: ${DEEPSEEK_API_KEY}
    model: deepseek-chat
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    model: claude-sonnet-4-20250514
```

### 3.2 ToolRegistry（`tools/registry.py`）

工具通过装饰器自注册，运行时按 Skill 白名单过滤。

```python
tool_registry = ToolRegistry()

@tool_registry.register(
    name="query_data",
    description="查询业务对象数据",
    parameters={
        "object_type": {"type": "string", "required": True, "description": "对象名称"},
        "filters": {"type": "array", "required": False, "description": "过滤条件"},
        "columns": {"type": "array", "required": False, "description": "返回字段"},
        "limit": {"type": "integer", "required": False, "description": "最大行数"},
    },
)
async def query_data(ctx: ToolContext, object_type: str, **kwargs) -> ToolResult:
    ...
```

核心能力：

- `registry.get_specs(whitelist)` → 返回过滤后的 OpenAI/Anthropic tool schema
- `registry.execute(name, params, ctx)` → 执行工具，返回统一 `ToolResult`
- `ToolContext` 携带 tenant_id、project_id、db session、omaha_service 等依赖

### 3.3 PermissionEnforcer（`tools/permission.py`）

工具执行前的权限校验层。

```python
class PermissionEnforcer:
    def check(self, tenant_id: int, tool_name: str, params: dict) -> bool:
        """检查租户是否有权调用该工具。"""
```

规则来源：

- 租户级别：哪些工具可用（免费版 vs 付费版）
- 项目级别：数据隔离（只能查询本项目的对象）
- Skill 级别：当前 Skill 的工具白名单

### 3.4 Skill 系统（`skills/`）

Skill 是一段结构化的 prompt + 工具白名单，存储为 YAML 文件。

```yaml
# skills/definitions/data_query.yaml
name: data_query
description: 数据查询与分析
trigger_keywords: ["查询", "多少", "分析", "趋势", "对比"]
system_prompt: |
  你是数据分析专家。用户已完成数据建模，现在需要查询和分析业务数据。
  - 任何涉及具体数据的问题，必须先调用工具查询
  - 查询一次后立即基于结果回答，不要反复查询
  - 如果数据触发健康规则阈值，主动提醒
allowed_tools:
  - query_data
  - list_objects
  - get_schema
  - get_relationships
  - generate_chart
  - save_asset
  - screen_stocks
```

预定义 Skill：

| Skill | 触发场景 | 工具白名单 |
|-------|---------|-----------|
| `onboarding` | 新项目，setup_stage=idle | （无工具，纯引导对话） |
| `data_ingestion` | 数据接入阶段 | upload_file, assess_quality, clean_data |
| `data_modeling` | 建模阶段 | load_template, scan_tables, infer_ontology, confirm_ontology, edit_ontology |
| `data_query` | 查询分析（默认） | query_data, list_objects, get_schema, get_relationships, generate_chart, save_asset, screen_stocks |

SkillResolver 逻辑：

1. 优先按 `setup_stage` 匹配（idle→onboarding, connecting→data_ingestion, modeling→data_modeling, ready→data_query）
2. ready 阶段下，按用户消息关键词二次匹配（如用户说"修改对象"→切换到 data_modeling skill）
3. 匹配结果：加载对应 Skill 的 system_prompt 片段 + 过滤 ToolRegistry 到白名单工具

### 3.5 ConversationRuntime（`runtime/conversation.py`）

会话状态管理，对应 claw-code 的 runtime crate。

```python
class ConversationRuntime:
    def __init__(self, session: ChatSession, skill: Skill, provider: ProviderAdapter):
        self.session = session
        self.skill = skill
        self.provider = provider
        self.messages: list[Message] = []

    def build_system_prompt(self, ontology_context: dict) -> str:
        """组装系统提示：基础模板 + Skill prompt + 本体上下文 + 健康规则 + 业务目标"""

    def append_user_message(self, content: str) -> None: ...
    def append_assistant_message(self, content: str, tool_calls: list) -> None: ...
    def append_tool_result(self, tool_call_id: str, result: str) -> None: ...

    def get_messages_for_llm(self) -> list[dict]:
        """返回格式化后的消息列表，处理上下文窗口截断"""
```

职责：

- 消息历史管理（追加、截断、持久化到 ChatMessage 表）
- 系统提示组装（合并 Skill prompt + 本体上下文 + onboarding 状态）
- 上下文窗口管理（消息过长时截断早期历史）
- 结构化输出解析（提取 `structured` 代码块中的 JSON）

### 3.6 Orchestrator（`orchestrator/`）

多 Agent 协调层，对应 claw-code 的 OmO。

**Coordinator** 是入口，负责意图复杂度判断：

```python
class Coordinator:
    async def handle(self, runtime: ConversationRuntime, user_message: str) -> AgentResponse:
        complexity = self._assess_complexity(user_message, runtime.skill)
        if complexity == "simple":
            return await self.executor.run(runtime)
        else:
            plan = await self.planner.plan(runtime)
            results = []
            for step in plan.steps:
                result = await self.executor.run_step(runtime, step)
                results.append(result)
            return await self.reviewer.review(runtime, plan, results)
```

**复杂度判断标准：**

- 简单：单对象查询、schema 查看、图表生成 → 单 Executor
- 复杂：跨对象分析、多步骤建模、涉及数据清洗+建模+查询的组合任务 → P/E/R

**ExecutorAgent**：核心 ReAct 循环，从现有代码迁移。

```python
class ExecutorAgent:
    async def run(self, runtime: ConversationRuntime) -> AgentResponse:
        """标准 ReAct 循环：思考→行动→观察→回答，最多 max_iterations 轮"""
```

**PlannerAgent**：接收用户意图，输出执行计划。

```python
class PlannerAgent:
    async def plan(self, runtime: ConversationRuntime) -> ExecutionPlan:
        """调用 LLM 分解任务为有序步骤列表"""
```

**ReviewerAgent**：校验执行结果的完整性和正确性。

```python
class ReviewerAgent:
    async def review(self, runtime: ConversationRuntime, plan: ExecutionPlan, results: list) -> AgentResponse:
        """检查：所有步骤是否完成、数据是否合理、是否需要补充查询"""
```

### 3.7 EventBus（`events/`）

进程内事件发布/订阅，对应 claw-code 的 clawhip。

```python
class EventBus:
    _handlers: dict[str, list[Callable]]

    def on(self, event_type: str, handler: Callable) -> None: ...
    async def emit(self, event: Event) -> None: ...
```

事件类型：

| 事件 | 触发时机 | 默认处理 |
|------|---------|---------|
| `tool.executed` | 任何工具执行完成 | 审计日志 |
| `tool.failed` | 工具执行失败 | 错误日志 + 通知 |
| `ontology.confirmed` | 用户确认建模 | 更新 setup_stage |
| `data.ingested` | 数据接入完成 | 触发质量评估 |
| `health.alert` | 查询结果触发健康规则 | 前端通知 |
| `session.started` | 新会话创建 | 加载历史上下文 |
| `session.completed` | 会话结束 | 持久化统计 |

第一版实现：定义接口 + `tool.executed` 审计日志 handler。其余 handler 后续按需补充。

### 3.8 瘦 chat_service.py（入口层）

重构后的 chat_service.py 只做组装：

```python
class ChatService:
    async def send_message(self, project_id, session_id, message, db) -> AgentResponse:
        # 1. 加载会话
        session = SessionManager.load(db, session_id)

        # 2. 解析 Skill
        skill = SkillResolver.resolve(session.setup_stage, message)

        # 3. 构建 Provider
        provider = ProviderFactory.create(config)

        # 4. 构建 Runtime
        runtime = ConversationRuntime(session, skill, provider)
        runtime.build_system_prompt(ontology_context)
        runtime.append_user_message(message)

        # 5. 交给 Coordinator 执行
        response = await Coordinator(
            executor=ExecutorAgent(tool_registry, event_bus),
            planner=PlannerAgent(provider),
            reviewer=ReviewerAgent(provider),
        ).handle(runtime, message)

        # 6. 持久化 + 返回
        session.save_messages(db)
        return response
```

## 4. 目录结构

```
backend/app/services/agent/
├── providers/
│   ├── __init__.py
│   ├── base.py              # ProviderAdapter ABC, LLMResponse, ToolCall, Message
│   ├── openai_compat.py     # OpenAICompatAdapter
│   └── anthropic.py         # AnthropicAdapter
├── runtime/
│   ├── __init__.py
│   ├── conversation.py      # ConversationRuntime
│   └── session.py           # SessionManager（复用 ChatSession 模型）
├── tools/
│   ├── __init__.py
│   ├── registry.py          # ToolRegistry, @register_tool, ToolContext, ToolResult
│   ├── permission.py        # PermissionEnforcer
│   └── builtin/
│       ├── __init__.py
│       ├── query.py         # query_data, list_objects, get_schema, get_relationships
│       ├── modeling.py      # scan_tables, infer_ontology, confirm_ontology, edit_ontology
│       ├── ingestion.py     # upload_file, assess_quality, clean_data
│       ├── chart.py         # generate_chart
│       └── asset.py         # save_asset, list_assets, get_lineage
├── skills/
│   ├── __init__.py
│   ├── loader.py            # SkillLoader
│   ├── resolver.py          # SkillResolver
│   └── definitions/
│       ├── onboarding.yaml
│       ├── data_ingestion.yaml
│       ├── data_modeling.yaml
│       └── data_query.yaml
├── orchestrator/
│   ├── __init__.py
│   ├── coordinator.py       # Coordinator（意图复杂度判断 + 路由）
│   ├── planner.py           # PlannerAgent
│   ├── executor.py          # ExecutorAgent（ReAct 循环）
│   └── reviewer.py          # ReviewerAgent
├── events/
│   ├── __init__.py
│   ├── bus.py               # EventBus
│   ├── types.py             # Event 类型定义
│   └── handlers/
│       ├── __init__.py
│       └── audit.py         # 审计日志 handler
└── chat_service.py           # 瘦入口（~100 行）
```

## 5. 数据流

### 5.1 简单查询："上个月销售额多少"

```
用户消息
  → ChatService.send_message()
  → SkillResolver → data_query skill
  → ConversationRuntime 组装系统提示（skill prompt + 本体上下文）
  → Coordinator._assess_complexity() → "simple"
  → ExecutorAgent.run()（ReAct 循环）
    → LLM 决定调用 query_data
    → PermissionEnforcer.check() → 通过
    → ToolRegistry.execute("query_data", params, ctx)
    → EventBus.emit(ToolExecuted)
    → LLM 基于结果生成回答
  → 返回 AgentResponse（message + data_table + chart_config）
```

### 5.2 复杂任务："帮我把这个 Excel 整理成业务对象"

```
用户消息
  → ChatService.send_message()
  → SkillResolver → data_modeling skill（因为 setup_stage=modeling 或关键词匹配）
  → Coordinator._assess_complexity() → "complex"
  → PlannerAgent.plan()
    → LLM 输出计划：[scan_tables → infer_ontology → 等待用户确认 → confirm_ontology]
  → ExecutorAgent.run_step(step1: scan_tables)
    → EventBus.emit(ToolExecuted)
  → ExecutorAgent.run_step(step2: infer_ontology)
    → EventBus.emit(ToolExecuted)
  → ReviewerAgent.review()
    → 检查推断结果完整性，生成 ontology_preview 结构化块
  → 返回 AgentResponse（message + structured ontology_preview）
  → 用户说"确认" → confirm_ontology → EventBus.emit(OntologyConfirmed)
```

## 6. 迁移策略

现有工具逻辑直接迁移，不重写业务代码：

| 现有文件 | 迁移目标 | 改动 |
|---------|---------|------|
| `toolkit.py` 中的 `_query_data()` | `tools/builtin/query.py` | 提取为独立函数 + `@register_tool` |
| `toolkit.py` 中的 `_infer_ontology()` 等 | `tools/builtin/modeling.py` | 同上 |
| `toolkit.py` 中的 `_upload_file()` 等 | `tools/builtin/ingestion.py` | 同上 |
| `chart_engine.py` | `tools/builtin/chart.py` | 整体迁移 |
| `react.py` 中的 `ONBOARDING_PROMPTS` | `skills/definitions/onboarding.yaml` | 转为 YAML |
| `react.py` 中的 `SYSTEM_PROMPT_TEMPLATE` | `runtime/conversation.py` | 拆分为基础模板 + Skill 注入 |
| `chat_service.py` 中的 `_call_openai()` | `providers/openai_compat.py` | 提取为 Adapter |
| `chat_service.py` 中的 `_call_anthropic()` | `providers/anthropic.py` | 提取为 Adapter |
| `chat_service.py` 中的 ReAct 循环 | `orchestrator/executor.py` | 提取为 ExecutorAgent |

## 7. 实施优先级

```
P0（核心，必须先完成）:
  - ProviderAdapter 抽象层
  - ToolRegistry + @register_tool + ToolContext
  - 内置工具迁移（query/modeling/ingestion/chart/asset）
  - ConversationRuntime
  - ExecutorAgent（ReAct 循环迁移）
  - 瘦 chat_service.py
  - Skill 定义 + SkillLoader + SkillResolver
  - 渐进式本体确认（field_confirm 交互块 + 置信度策略）
  - SnapshotManager + undo_last 工具

P1（增强）:
  - PermissionEnforcer
  - Coordinator（复杂度判断 + 路由）
  - PlannerAgent + ReviewerAgent
  - 预置连接器：金蝶云、飞书多维表格 + 对应 Skill 变体

P2（补全）:
  - EventBus + 事件类型定义
  - 审计日志 handler
  - 其余事件 handler（notification, lifecycle）
  - MCP 通用桥接（供自定义连接器使用）
  - 用友畅捷通、企业微信连接器
```

## 8. 测试策略

- 每个模块独立可测：ToolRegistry 不依赖 LLM，Provider 可 mock，Skill 是纯 YAML 解析
- 现有 `tests/unit/agent/` 和 `tests/api/` 测试迁移到新结构
- 新增测试：ToolRegistry 注册/发现/执行、SkillResolver 匹配逻辑、Coordinator 路由逻辑
- 集成测试：完整 ChatService.send_message() 流程（mock LLM 响应）

## 9. 渐进式本体确认

当前 `infer_ontology → confirm_ontology` 的一次性确认流程对非技术用户风险太高。改为逐步引导：

### 9.1 确认流程

```
infer_ontology 返回草稿
  → Agent 逐对象展示（不是一次性全部）
  → 对每个对象：
    1. "我发现了一个【客户】对象，包含这些字段："
    2. 逐字段确认："【手机号】这列看起来是联系方式，对吗？"
    3. 用户可以：确认 / 改名 / 跳过 / 标记为"不确定"
  → 所有对象确认完毕后，展示完整本体预览
  → 用户最终确认 → confirm_ontology
```

### 9.2 结构化交互块

新增 `field_confirm` 类型的结构化输出：

```json
{
  "type": "panel",
  "panel_type": "field_confirm",
  "content": "这列数据看起来是【客户姓名】",
  "data": {
    "object_name": "客户",
    "field_name": "name",
    "inferred_type": "string",
    "inferred_semantic_type": "person_name",
    "sample_values": ["张三", "李四", "王五"],
    "confidence": 0.92
  },
  "options": [
    {"label": "没错", "value": "confirm"},
    {"label": "改个名字", "value": "rename"},
    {"label": "这列不需要", "value": "skip"},
    {"label": "不确定", "value": "unsure"}
  ]
}
```

### 9.3 置信度策略

- 高置信度（>0.9）：展示但默认确认，用户可改
- 中置信度（0.6-0.9）：必须用户明确确认
- 低置信度（<0.6）：主动询问"这列是什么意思？"

这样 agent 只在不确定的地方打扰用户，高置信度字段快速通过。

## 10. 预置行业连接器

MCP bridge 作为通用扩展机制保留，但第一版必须提供开箱即用的数据接入方式：

### 10.1 第一版支持的数据源

| 数据源 | 接入方式 | 优先级 |
|--------|---------|--------|
| Excel/CSV 文件上传 | 直接解析（已有） | P0 |
| 金蝶云星空 | REST API 连接器 | P1 |
| 飞书多维表格 | 飞书开放平台 API | P1 |
| MySQL/PostgreSQL 直连 | SQL 连接器（已有） | P0 |
| 用友畅捷通 T+ | REST API 连接器 | P2 |
| 企业微信导出 | CSV 解析 + 格式适配 | P2 |

### 10.2 连接器与 Skill 的关系

每个连接器对应一个接入 Skill 变体：

```yaml
# skills/definitions/ingestion_kingdee.yaml
name: ingestion_kingdee
description: 金蝶云数据接入
extends: data_ingestion
system_prompt: |
  用户正在接入金蝶云星空的数据。
  引导用户提供：金蝶云地址、账号、数据中心ID。
  连接成功后自动拉取科目表和凭证数据。
allowed_tools:
  - connect_kingdee
  - assess_quality
  - clean_data
connector: kingdee_cloud
```

### 10.3 对话式接入流程

```
用户："我用金蝶管账"
  → SkillResolver 匹配 ingestion_kingdee skill
  → Agent："好的，请提供你的金蝶云地址和账号"
  → 用户提供凭据
  → Agent 调用 connect_kingdee 工具
  → 自动拉取数据 → assess_quality → 展示质量报告
```

用户不需要知道 MCP 是什么，也不需要部署任何东西。

## 11. 操作可逆性

所有写操作（清洗、建模、编辑本体）支持撤销。

### 11.1 快照机制

```python
class SnapshotManager:
    async def take(self, project_id: int, operation: str, data: dict) -> int:
        """在写操作前保存快照，返回 snapshot_id"""

    async def restore(self, snapshot_id: int) -> None:
        """恢复到指定快照"""

    async def list(self, project_id: int, limit: int = 10) -> list[Snapshot]:
        """列出最近的快照"""
```

### 11.2 快照触发点

| 操作 | 快照内容 |
|------|---------|
| `clean_data` | 清洗前的原始数据副本 |
| `confirm_ontology` | 确认前的本体草稿状态 |
| `edit_ontology` | 编辑前的本体快照 |

### 11.3 撤销交互

用户说"撤销"或"回到上一步"时：

```
Agent："上一步操作是【确认建模】，要恢复到建模前的状态吗？"
  → 用户确认
  → SnapshotManager.restore()
  → setup_stage 回退
  → Agent："已恢复，我们重新来过。"
```

新增工具：

```yaml
- name: undo_last
  description: 撤销上一步写操作，恢复到之前的状态
  allowed_in: [data_ingestion, data_modeling, data_query]
```

### 11.4 快照存储

- 本体快照：存储在 `ontology_snapshots` 表（JSON 格式）
- 数据快照：对于小数据集（<10MB）存完整副本；大数据集只存操作日志（可重放）
- 保留最近 20 个快照，超出自动清理

## 12. 不做的事

- 不引入外部 Agent 框架（LangChain/LangGraph/CrewAI）
- 不改变前端 API 接口（ChatService 的输入输出格式保持兼容）
- 不重写工具的业务逻辑（query_data 内部的 OmahaService 调用不变）
- 不在此次重构中实现 streaming（作为后续独立任务）



