# Phase 3 Design Spec: Ontology-Agent Integration

**Date:** 2026-03-15
**Status:** Approved
**Author:** Brainstorming Session

---

## Overview

Phase 3 打通 Ontology 层与 Agent 的通信，实现两个核心目标：

1. **MCP Server** — 将 Ontology 层完整暴露为 MCP 工具，支持任何兼容 MCP 的外部 Agent（Claude Desktop、Cursor、OpenClaw 等）通过 API Key 直接访问项目数据
2. **内置对话界面** — 平台内嵌多轮对话 Agent，支持中文自然语言查询、自动图表生成

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   外部 Agent                         │
│  (Claude Desktop / Cursor / OpenClaw / 自定义)       │
└──────────────────┬──────────────────────────────────┘
                   │ MCP Protocol (stdio / HTTP SSE)
┌──────────────────▼──────────────────────────────────┐
│              MCP Server                              │
│  工具: list_objects, get_schema, get_relationships,  │
│        query_data, save_asset, list_assets,          │
│        get_lineage                                   │
│  认证: API Key (X-API-Key header)                    │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│           OntologyService (已有，复用)               │
│  omaha_service.query_objects()                       │
│  omaha_service.get_relationships()                   │
│  omaha_service.get_object_schema()                   │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              数据库 (SQLite / MySQL)                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│           内置对话界面                               │
│  ChatAgent UI → ChatService → LLM                   │
│              → MCP 工具调用                          │
│              → ECharts 图表渲染                      │
└─────────────────────────────────────────────────────┘
```

**核心原则：** MCP 工具是唯一的数据访问层，内置 Agent 和外部 Agent 共享同一套工具实现，不重复逻辑。

---

## Phase 3.1: MCP Server

### MCP Tools (7个)

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `list_objects` | 列出项目所有 Ontology 对象类型 | — |
| `get_schema` | 获取对象字段定义 | `object_type` |
| `get_relationships` | 获取对象间关系 | `object_type` |
| `query_data` | 执行查询（列选择、过滤、JOIN） | `object_type, selected_columns?, filters?, joins?, limit?` |
| `save_asset` | 保存查询为资产 | `name, description?, base_object, selected_columns?, filters?, joins?, row_count?` |
| `list_assets` | 列出已保存资产 | — |
| `get_lineage` | 获取资产数据血缘 | `asset_id` |

### API Key 认证

- 新增 `project_api_keys` 表
- 每个项目可生成多个 Key，支持命名和撤销
- Key 格式：`omaha_<project_id>_<random_32chars>`
- 存储 SHA256 哈希，原始 Key 仅创建时返回一次
- 支持设置过期时间 `expires_at`

### MCP Server 启动方式

两种模式独立运行，认证机制不同：

```bash
# stdio 模式（标准 MCP，适合 Claude Desktop）
# API Key 通过环境变量传入，避免暴露在 ps aux
OMAHA_API_KEY=omaha_1_xxxxx python -m app.mcp.server

# Claude Desktop 配置示例 (claude_desktop_config.json):
# {
#   "mcpServers": {
#     "omaha": {
#       "command": "python",
#       "args": ["-m", "app.mcp.server"],
#       "env": { "OMAHA_API_KEY": "omaha_1_xxxxx" }
#     }
#   }
# }
```

```bash
# HTTP SSE 模式（适合 Web 集成，内置 ChatAgent 使用）
GET /api/v1/mcp/sse
Header: X-API-Key: omaha_1_xxxxx
```

`auth.py` 统一处理两种来源：stdio 模式读取 `os.environ["OMAHA_API_KEY"]`，SSE 模式读取 `X-API-Key` header。

### 新增文件

```
backend/app/mcp/
  __init__.py
  server.py          # MCP Server 主入口
  tools.py           # 7 个工具实现
  auth.py            # API Key 验证逻辑
backend/app/api/api_keys.py   # API Key CRUD 端点
backend/app/models/api_key.py # API Key 数据模型
backend/alembic/versions/003_add_phase3.py
```

### API Key 管理端点

```
POST   /api/v1/projects/{project_id}/api-keys        # 生成 Key
GET    /api/v1/projects/{project_id}/api-keys        # 列出 Keys
DELETE /api/v1/projects/{project_id}/api-keys/{id}  # 撤销 Key
```

---

## Phase 3.2: 内置对话界面

### 交互流程

```
用户输入中文问题
      ↓
POST /api/v1/chat/{project_id}/message
      ↓
ChatService:
  1. 加载 session 历史（多轮上下文）
  2. 构建系统提示（注入 Ontology 上下文）
  3. 调用 LLM（DeepSeek / Claude / OpenAI）
  4. LLM 决定调用哪些 MCP 工具
  5. 执行工具，获取数据
  6. LLM 生成回答 + 图表配置（ECharts JSON）
      ↓
返回: { message, data_table?, chart_config?, sql? }
      ↓
前端渲染：对话气泡 + 数据表格 + ECharts 图表
```

### 图表自动选择策略

| 数据特征 | 图表类型 |
|----------|----------|
| 时间序列（含日期列） | 折线图 |
| 分类 + 数值（≤10类） | 柱状图 |
| 占比分析（求和=100%） | 饼图 |
| 两个数值列 | 散点图 |
| 其他 | 仅表格 |

### 多轮对话

- `chat_sessions` 表存储会话元数据，`chat_messages` 表存储每条消息
- 每次请求携带 `session_id`，后端按时间顺序加载历史消息（最近 N 条）
- `title` 自动取第一条消息前 20 字
- 支持新建会话、切换会话、删除会话

### 新增文件

```
backend/app/services/chat.py       # ChatService（LLM 调用 + 工具执行）
backend/app/api/chat.py            # Chat API 端点
backend/app/models/chat_session.py # 会话 + 消息数据模型
frontend/src/pages/ChatAgent.tsx   # 对话界面
frontend/src/services/chat.ts      # Chat API 服务
```

### ChatService 伪代码骨架

```python
class ChatService:
    def send_message(self, session_id, user_message, project_id):
        # 1. 加载历史消息（最近20条）
        history = self._load_history(session_id, limit=20)

        # 2. 构建系统提示（注入 Ontology 上下文）
        ontology_ctx = self._build_ontology_context(project_id)
        system_prompt = SYSTEM_TEMPLATE.format(ontology=ontology_ctx)

        # 3. 定义 MCP 工具 schema（LLM function calling 格式）
        tools = self._get_tool_schemas()  # 7个工具的 JSON schema

        # 4. 调用 LLM（原生 function calling API，不依赖 LangChain）
        response = llm.chat(
            messages=[{"role": "system", "content": system_prompt}]
                     + history
                     + [{"role": "user", "content": user_message}],
            tools=tools
        )

        # 5. 执行工具调用（循环直到 LLM 不再调用工具）
        while response.tool_calls:
            tool_results = [self._execute_tool(tc) for tc in response.tool_calls]
            response = llm.chat(..., tool_results=tool_results)

        # 6. 后端规则引擎决定图表类型（不依赖 LLM）
        chart_config = self._build_chart_config(last_query_result)

        # 7. 保存消息到 chat_messages 表
        self._save_messages(session_id, user_message, response, chart_config)

        return {"message": response.text, "data_table": ..., "chart_config": chart_config}
```

**关键决策：**
- 使用各 LLM 原生 function calling API（不引入 LangChain），减少依赖
- 图表类型由后端规则引擎决定（见图表自动选择策略表），不由 LLM 生成，避免格式错误
- `chart_config` 在响应中为 optional，前端做 JSON schema 校验后再渲染，校验失败降级为纯表格

### Chat API 端点

```
POST /api/v1/chat/{project_id}/sessions          # 新建会话
GET  /api/v1/chat/{project_id}/sessions          # 列出会话
POST /api/v1/chat/{project_id}/sessions/{id}/message  # 发送消息
DELETE /api/v1/chat/{project_id}/sessions/{id}   # 删除会话
```

---

## Database Schema

### project_api_keys

```sql
CREATE TABLE project_api_keys (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    name        VARCHAR NOT NULL,          -- 用户自定义名称
    key_hash    VARCHAR NOT NULL UNIQUE,   -- SHA256(original_key)
    key_prefix  VARCHAR NOT NULL,          -- random部分前8位，如 "a3f9b2c1"
    is_active   BOOLEAN DEFAULT TRUE,
    expires_at  DATETIME,
    created_by  INTEGER NOT NULL REFERENCES users(id),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### chat_sessions

```sql
CREATE TABLE chat_sessions (
    id          INTEGER PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    user_id     INTEGER NOT NULL REFERENCES users(id),
    title       VARCHAR,                   -- 自动取第一条消息前20字
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME
);
```

### chat_messages

```sql
CREATE TABLE chat_messages (
    id           INTEGER PRIMARY KEY,
    session_id   INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role         VARCHAR NOT NULL,         -- 'user' | 'assistant' | 'tool'
    content      TEXT NOT NULL,
    tool_calls   TEXT,                     -- JSON，LLM 工具调用记录
    chart_config TEXT,                     -- JSON，ECharts 配置（optional）
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## Implementation Order

### Week 1: MCP Server
1. `project_api_keys` 模型 + 迁移
2. API Key 生成/撤销端点
3. MCP Server 核心（7 个工具 + API Key 认证）
4. 验证：Claude Desktop 接入测试

### Week 2: Chat Backend
5. `chat_sessions` 模型 + 迁移
6. ChatService（LLM 调用 + 工具执行 + 多轮上下文）
7. Chat API 端点

### Week 3: Chat Frontend
8. ChatAgent 前端页面（对话 UI + 表格 + ECharts）
9. 路由集成（`/projects/:id/chat`）
10. 端到端测试

---

## Success Criteria

### Phase 3.1 (MCP Server)
- [ ] Claude Desktop 可通过 API Key 连接项目
- [ ] 7 个 MCP 工具全部可用
- [ ] API Key 可生成、列出、撤销
- [ ] 过期 Key 自动拒绝访问
- [ ] `query_data` 工具响应时间 ≤5s（limit≤1000行）
- [ ] 无效/过期 Key 返回明确错误信息（401）

### Phase 3.2 (内置对话)
- [ ] 用户可用中文提问，获得数据结果
- [ ] 多轮对话保持上下文（最近20条消息）
- [ ] 自动生成 ECharts 图表，chart_config 校验失败时降级为纯表格
- [ ] 支持 DeepSeek / Claude / OpenAI 三种 LLM
- [ ] LLM 调用超时（>30s）或限流时，返回友好错误提示而非崩溃
- [ ] 单次对话响应时间 ≤15s（含 LLM 调用）

---

## Security Considerations

- API Key 原始值仅创建时返回一次，后端只存哈希
- MCP 工具只允许读取和保存资产，不允许修改 Ontology 配置
- 所有 SQL 查询继续使用参数化查询，防止注入
- API Key 与 project_id 绑定，无法跨项目访问

---

## Dependencies

### Backend
- `mcp` — Python MCP SDK (`pip install mcp`)
- 各 LLM 原生 SDK：`openai`、`anthropic`、`requests`（DeepSeek）— 已有

### Frontend
- `echarts` + `echarts-for-react` — 图表渲染
- `@ant-design/icons` — 已有

---

## Out of Scope (Phase 4+)

- 血缘可视化图谱
- 资产版本控制
- 多用户协作权限
- 定时刷新资产
- 数据质量评分
