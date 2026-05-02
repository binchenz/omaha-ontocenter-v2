# 中国中小企业 Palantir — AI 原生数据平台设计文档

**日期**: 2026-05-01
**版本**: v1.0 (MVP Design)
**团队规模**: 2-5 人

---

## 产品定位

面向中国中小企业的 AI 原生数据平台，三大支柱：

1. **本体引擎**：将分散的企业数据转化为语义本体（Ontology），以 OAG（Ontology-Augmented Generation）为 Agent 提供无幻觉查询
2. **MCP + Skill 分发**：本体暴露为 MCP Server + 可安装 Skill，供给下游 Agent（Claude Code、OpenClaw、LangGraph）
3. **平台 Agent**：内置 ReAct + Planning 双引擎 Agent，装载本体工具和 Skill，对话式操作数据

**目标用户**：30-50 岁中小企业老板（主要）+ 技术分析师（次要）

**领域通用**：电商分析、跨境电商、供应链管理、财务数据、App 运营、博物馆藏品知识体系、网络小说拆解 — 从第一天起就是多领域框架

**美学**：复古未来主义 × 瑞士实用设计融合

---

## 一、系统全景

```
┌──────────────────────────────────────────────────────────────┐
│                    Next.js BFF (TypeScript)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ 认证     │  │ Agent UI │  │ 本体管理  │  │ Skill 展示    │ │
│  │ NextAuth │  │ Chat     │  │ Schema   │  │ 数据中心      │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘ │
│       │              │              │                │         │
│       └──────────────┴──────────────┴────────────────┘         │
│                           │ HTTP + SSE                         │
└───────────────────────────┼───────────────────────────────────┘
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              Python FastAPI (核心引擎)                         │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐              │
│  │ 数据摄入   │  │ OAG 查询 │  │ MCP 工厂     │              │
│  │ (Ingest)   │  │ 引擎     │  │ 动态生成     │              │
│  └─────┬──────┘  └────┬─────┘  └──────┬───────┘              │
│        │               │                │                       │
│  ┌─────┴───────────────┴────────────────┴───────┐              │
│  │ 本体推断引擎 (规则 + LLM 复核)                │              │
│  └───────────────────────┬──────────────────────┘              │
│                          │                                     │
│  ┌───────────────────────┴──────────────────────┐              │
│  │ delta-rs + DuckDB (数据版本化 + 查询)        │              │
│  └──────────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
        ┌─────────┐  ┌──────────┐  ┌──────────┐
        │PostgreSQL│  │Delta Lake│  │S3/MinIO  │
        │(元数据)  │  │(数据副本)│  │(Delta存储)│
        └─────────┘  └──────────┘  └──────────┘
```

**架构原则**：
- Next.js BFF 层只做 Agent 逻辑、呈现和认证，不做数据分析
- Python FastAPI 管所有数据处理：摄入、本体推断、OAG 查询、MCP 生成
- 两服务间 HTTP + SSE 通信，严格 TypeScript/Pydantic 契约
- 同一代码库：SaaS (Railway) 和本地部署 (Docker Compose) 用同一套镜像

---

## 二、本体引擎

### 2.1 虚拟投射 + 数据同步

本体是数据源之上的**语义投影层**。源系统数据定期同步到平台，本体存的是**映射配置**：

```
源系统（不改动）              平台内（副本 + 本体）
┌──────────┐              ┌────────────────────┐
│ 金蝶(月) │── 定时sync ─▶│ orders_snapshot     │──┐
│ 用友(时) │── 定时sync ─▶│ finance_snapshot    │──┤
│ CSV上传  │── 一次导入 ─▶│ products_uploaded   │──┤
└──────────┘              │                      │
                          │  本体投影层           │
                          │  Order ──→ Customer  │
                          └──────────────────────┘
```

### 2.2 OAG（Ontology-Augmented Generation）

Agent 查询本体时返回**结构化对象图**而非表格文本，LLM 拿到的是完整关系图，不猜测对象间关系 — 这是防幻觉机制。

```json
// Agent 调用 search_orders("查询延迟订单")
{
  "object_type": "Order",
  "matched": [
    {
      "id": "ORD-001",
      "label": "PO-2026-0420",
      "properties": {
        "amount": {"value": 52000, "semantic_type": "currency", "unit": "CNY"},
        "status": {"value": "delayed", "semantic_type": "enum"},
        "created_at": {"value": "2026-04-20", "semantic_type": "date"}
      },
      "links": {
        "customer": {"object_type": "Customer", "id": "C-89", "label": "深圳XX科技"},
        "supplier": {"object_type": "Supplier", "id": "S-12", "label": "东莞XX工厂"}
      },
      "available_functions": ["risk_score", "delay_reason_analysis"]
    }
  ],
  "context": {
    "total": 1,
    "related_objects": ["Customer", "Supplier", "Shipping"],
    "suggested_queries": ["查看供应商历史交付率", "对比同类订单平均时效"]
  }
}
```

### 2.3 Function 绑定

本体注册 Python 函数，Agent 调用函数执行计算而非让 LLM 裸算：

```yaml
object: Order
fields:
  - name: amount
    type: float
    semantic_type: currency
    unit: CNY
  - name: risk_score
    type: computed
    function: order_risk_scorer

functions:
  order_risk_scorer:
    handler: functions.risk.order_risk_scorer
    description: "基于客户历史、金额、季节因素计算订单风险分"
    input: [order_id]
    output: {score: float, factors: list}
    caching: 1h
```

### 2.4 Palantir 三层模型对照

| 层 | Palantir | 我们的 MVP |
|---|---|---|
| Semantic (静态对象/链接) | Ontology objects + links | YAML 本体定义 + OAG 查询 |
| Kinetic (Action/Function/Writeback) | Action Types + Functions | Python Function 绑定 |
| Dynamic (AI/仿真) | AIP Agent Studio + 仿真引擎 | Planning + ReAct Agent（见第三节） |

### 2.5 MDO 多源对象

单个本体对象可跨多个物理数据源：

```yaml
Object: Order
  properties:
    - name: amount
      source: finance_dataset       # 月更新
    - name: shipping_status
      source: warehouse_dataset     # 小时更新
```

查询时按主键实时拼装，返回时每个字段标注数据来源和新鲜度：

```json
{
  "amount": {"value": 52000, "source": "金蝶财务", "last_updated": "2026-04-01"},
  "shipping_status": {"value": "已发货", "source": "仓库WMS", "last_updated": "2026-05-01 11:00"}
}
```

---

## 三、平台 Agent 引擎

### 3.1 双引擎架构

Planning 和 ReAct 分离：

```
用户提问 → Planning Agent（制定计划）→ 展示给用户确认
                ↓
         ReAct Agent（逐步执行）
         Think → 选 Tool → 执行 → Observe → Think...
                ↓
         最终回答 + 可视化
```

**分离的好处**：计划让用户可见可控，ReAct 循环中每步有 OAG 上下文防幻觉。

### 3.2 可用工具

ReAct 循环中 Agent 可调用三类工具：

| 类别 | 工具 | 来源 |
|---|---|---|
| 本体工具（动态生成） | `search_订单`, `count_订单`, `aggregate_订单`, `navigate_path`, `call_function` | 本体 YAML 自动生成 |
| 通用工具 | `chart_render`, `export_csv`, `web_search`, `code_execute` | 平台内置 |
| Skill 工具 | `skill:电商分析`, `skill:财务审计` | 用户从能力中心安装 |

### 3.3 跨本体支持

用户可同时有多个本体（电商、财务、供应链），Agent 自动判断问题涉及哪些本体并装载对应工具。一个问题可能触发跨本体导航。

### 3.4 计划展示（针对老板视角优化）

**默认展示业务语言**：\"1. 查看各品类收入变化 2. 找毛利异常品类 3. 排查供应商影响\"

**技术细节可折叠**：tool 名称、JSON 参数、依赖关系默认隐藏，技术用户可展开。

### 3.5 会话状态

```typescript
ChatSession {
  messages[]           // 对话历史
  active_ontology_ids  // 当前装载的本体
  installed_skills     // 已安装的 skill
  plan                 // 当前执行计划 (JSON, nullable)
  oag_cache            // OAG 上下文缓存
}
```

---

## 四、MCP + Skill 分发层

### 4.1 MCP Server 工厂

根据本体自动生成 MCP Server，暴露标准化工具：

- `search_{slug}` — 搜索本体对象
- `count_{slug}` — 计数
- `aggregate_{slug}` — 聚合查询
- `navigate_path` — 多跳路径导航
- `call_function` — 调用本体注册的 Python 函数

一个本体 → 一个 MCP Server，用户可在平台内一键启动/停止。

### 4.2 Skill 打包

遵循 skill-creator 范式，每个 Skill 包含：

```
my-skill/
├── SKILL.md           # 元数据 + 使用说明
├── mcp-config.json    # MCP Server 连接配置
└── examples/          # 使用示例
```

Skill 从平台下载安装到 Claude Code / OpenClaw / LangGraph 中，Agent 获得对应本体的查询能力。

### 4.3 能力中心（非\"Skill 市场\"）

面向老板用户的命名 — 展示可安装的 Skill 列表，附带描述、使用示例和安装量。MVP 不做评分/评论系统。

---

## 五、前端设计系统

### 5.1 美学方向

复古未来主义 × 瑞士实用设计，60/40 比例融合（瑞士主导偏冷，调整为温暖平衡）。

### 5.2 设计令牌

```css
:root {
  --bg-root: #fafaf7;                  /* 页面根背景 */
  --bg-surface: #f3f2ed;               /* 卡片/面板背景 */
  --bg-data: #f5f4ee;                  /* 数据展示区（暖浅灰，非终端黑） */
  --accent: #c8842a;                   /* 琥珀主色 */
  --accent-glow: rgba(200, 132, 42, 0.08); /* 琥珀微光 */
  --cool: #5b7a8c;                     /* 冷色点缀（钢蓝） */
  --text-primary: #1c1c1a;             /* 主文字 */
  --text-secondary: #6b6a63;           /* 次要文字 */
  --text-data: #2a2820;                /* 数据展示文字 */
  --font-display: 'Inter', sans-serif;
  --font-body: 'Inter', sans-serif;
  --font-data: 'Inter', sans-serif;    /* 非 JetBrains Mono */
  font-feature-settings: 'tnum' 1;     /* 表格数字等宽对齐 */
}
```

**关键设计决定**：
- 数据区不搞黑色终端风 → 暖浅灰 `#f5f4ee`，和页面融为一体
- 不用等宽字体 → Inter + `tnum` 实现表格数字对齐，不给非技术用户"代码感"
- 8px 基线网格，所有间距为 8 的倍数

### 5.3 复古未来主义细节

- 琥珀色 hover 发光效果
- 扫描线式加载动画（subtle CRT scan-line）
- 边框用细线 + 微圆角
- 状态指示器用小圆点（绿/琥珀/灰）

### 5.4 核心页面

**Chat — Agent 对话**

```
┌─────────────────────────────────────────────┐
│  💬 华南区毛利为什么下降了？                  │
├─────────────────────────────────────────────┤
│  📋 计划（可折叠）                            │
│  1. 查华南区各品类收入/成本变化  ✅           │
│  2. 找出毛利下降异常品类          🔄 执行中  │
│  3. 排查供应商交付影响             ⏳        │
│                                              │
│  ┌─ Step 2 结果 ──────────────────────────┐ │
│  │  手机配件毛利下降 34%                   │ │
│  │  [数据表格，表头数字等宽对齐]           │ │
│  └────────────────────────────────────────┘ │
│                                              │
│  💡 建议追加：看促销活动影响？ [接受] [跳过]  │
└─────────────────────────────────────────────┘
```

关键交互：
- 计划默认业务语言，技术细节折叠
- 每步执行结果实时流式渲染
- Agent 可建议追加步骤，用户确认后执行
- 左侧问题摘要 sidebar（本次会话所有提问列表，点击回溯）

**本体详情 — 对象图可视化**
展示对象、字段、链接关系。借鉴现有 OntoCenter 的 OntologyGraph 但简化交互。

**数据摄入向导**
三步：连接数据源 → 预览 Schema → 确认本体生成（规则推断 + LLM 复核建议）

### 5.5 页面路由

```
app/
├── (auth)/login, register
├── (app)/
│   ├── chat/              ★ 核心 Agent 对话
│   ├── ontology/          本体列表/创建/详情/摄入
│   ├── datasources/       数据源管理
│   ├── skills/            能力中心
│   └── settings/          账户 + API Key
```

---

## 六、API 契约

### 6.1 核心端点

```
Next.js BFF                          Python FastAPI
─────────                           ──────────────

# 数据摄入
POST /api/python/ingest          →  POST /ingest

# 本体操作
GET  /api/python/ontology/{id}   →  GET /ontology/{id}/schema
POST /api/python/ontology/{id}/query → POST /ontology/{id}/query

# MCP 生成
POST /api/python/ontology/{id}/mcp/generate

# 函数执行
POST /api/python/function/{name} → POST /function/{name}
```

### 6.2 核心契约：OAG 查询

```typescript
// 请求
interface QueryRequest {
  operation: "search" | "count" | "aggregate" | "navigate";
  object: string;
  filters?: Record<string, any>;
  measures?: string[];
  group_by?: string[];
  path?: string[];
  limit?: number;          // 默认 50
  include_links?: string[];
  include_functions?: string[];
}

// 响应（完整定义见第二节 OAG 示例）
interface QueryResponse {
  object_type: string;
  matched: Array<{
    id: string;
    label?: string;
    properties: Record<string, {
      value: any;
      semantic_type: string;
      unit?: string;
      format?: string;
    }>;
    links?: Record<string, { object_type: string; id: string; label: string }>;
    available_functions?: string[];
  }>;
  context: { total: number; related_objects?: string[]; suggested_queries?: string[]; };
}
```

### 6.3 错误格式

Python 返回的 error message **必须能直接展示给老板看**：
- 好的："数据源连接超时，请检查网络后重试"
- 坏的："ConnectionRefusedError: [Errno 61]"

```typescript
interface PythonError {
  error: {
    code: string;        // "QUERY_TIMEOUT" | "DATASOURCE_UNREACHABLE" | "INVALID_FILTER"
    message: string;     // 人类可读
    details?: Record<string, any>;
  };
}
```

---

## 七、部署架构

### 7.1 双模式

同一代码库，两套部署：

| 模式 | 目标 | 方式 |
|---|---|---|
| SaaS | 普通用户 | Railway 部署 |
| 本地部署 | 高价值客户 | Docker Compose 一键启动 |

### 7.2 Docker Compose

```yaml
# 本地部署包
services:
  postgres:
    image: postgres:16
  python-api:
    image: platform/python-api
    environment:
      - DATABASE_URL=postgresql://...
      - LLM_PROVIDER=openai|anthropic|ollama|vllm
      - LLM_API_KEY=${CLIENT_API_KEY}
      - DELTA_STORAGE=/data/delta
  nextjs:
    image: platform/nextjs
    environment:
      - PYTHON_API_URL=http://python-api:8000
```

本地部署时数据不出客户网络，客户提供自己的 LLM API Key（或对接 Ollama/vLLM）。

---

## 八、数据模型

### 8.1 核心实体

```
Tenant (租户)
├── User (用户, role: owner/analyst/viewer)
├── ApiKey (MCP 外部访问 token)
├── DataSource (连接配置, 加密存储)
│   └── Dataset (同步的数据副本)
│       ├── last_synced_at
│       ├── sync_schedule     # manual | hourly | daily | monthly
│       └── status            # syncing | ready | error
├── Ontology (本体)
│   ├── yaml_source           # 可读源格式 (导出/diff/git)
│   ├── version, status       # draft | published
│   ├── OntologyObject
│   │   ├── Property (name, slug, semantic_type, source_column)
│   │   └── 关联 Datasource + table_name
│   ├── Link (from_object → to_object, type: fk/value/multi)
│   ├── Function (name, handler Python路径, input/output schema, caching_ttl)
│   ├── MCPServer (endpoint, status: stopped/running)
│   └── Skill (name, version, package_url, installs_count)
└── ChatSession
    ├── ontology_ids (装载的本体)
    ├── plan (JSON, 当前计划)
    ├── oag_cache (上下文缓存)
    └── messages
```

### 8.2 存储策略

| 存储 | 内容 |
|---|---|
| PostgreSQL | 用户、租户、本体配置、Chat 会话等元数据 |
| Delta Lake 文件 | 从数据源同步的数据副本（不可变版本链） |
| S3 / MinIO | Delta Lake 文件的对象存储 |

### 8.3 关键设计决策

- **Ontology 双份存储**：YAML 文件 + DB 结构化记录，两者同步，版本号关联
- **Property.semantic_type 枚举**：`currency | percentage | date | datetime | enum | text | number | id | computed`
- **Delta Lake 时间旅行**：每次 sync 产生新版本，查询默认用最新，支持指定时间点回查
- **字段级数据新鲜度**：每个字段标注来源和最后更新时间

---

## 九、技术栈 + MVP 范围

### 9.1 技术栈

```
Next.js BFF                    Python FastAPI
────────────                   ──────────────
next.js 14+ (App Router)       fastapi + uvicorn
TypeScript                     deltalake (数据版本化)
Tailwind CSS                   duckdb (查询引擎)
shadcn/ui (组件基座)           pandas (数据清洗)
Vercel AI SDK (流式Agent)      sqlalchemy (连接器抽象)
Prisma (用户 CRUD)             pydantic (契约)
NextAuth (认证)                openai/anthropic SDK

存储                           部署
────                           ────
PostgreSQL (元数据)            Railway (SaaS)
Delta Lake (数据副本)          Docker Compose (本地)
S3/MinIO (Delta 存储)          同一代码库，同一 Docker 镜像
```

### 9.2 MVP 范围

| ✅ 做 | ❌ 不做 |
|---|---|
| CSV/Excel/SQLite/MySQL/PG 连接 | 复杂 Streaming/CDC sync |
| 规则引擎 + LLM 复核本体推断 | 全自动本体生成（人在 loop 确认） |
| OAG 结构化查询响应 | 语义搜索/向量检索 |
| ReAct + Planning Agent | 多 Agent 协作 |
| 对话中展示计划 + 逐步执行 | 用户手动编排计划 |
| MCP Server 动态生成（单本体） | 跨本体 MCP 联邦 |
| Skill 打包 + 注册表 | 评分/评论/市场 |
| 老板视图（业务语言） | 分析师视图（技术展开） |
| Delta Lake 版本化 + 时间点查询 | Nessie 分支/合并 |
| SaaS (Railway) + Docker Compose | K8s 集群/多租户隔离 |

---

## 附录 A：设计过程中的关键纠错

| # | 错误 | 修正 | 原因 |
|---|---|---|---|
| 1 | 不存储用户原始数据 | 必须同步数据副本到平台 | 查询性能和跨源一致性需要副本 |
| 2 | 计划展示技术细节 | 默认业务语言，技术可折叠 | 老板不理解 `aggregate_order` |
| 3 | 数据区深色背景 `#1e1e1c` | 改为暖浅灰 `#f5f4ee` | 终端黑在暖白页面上视觉割裂 |
| 4 | JetBrains Mono 等宽字体 | Inter + `tnum` 数字对齐 | 等宽字体给非技术用户"代码感"心理距离 |
| 5 | "Skill 市场" 命名 | "能力中心" / "工具箱" | 老板不知道什么是 Skill |
| 6 | 70/30 瑞士主导配色 | 调整为 60/40 + 琥珀光晕 | 纯瑞士太冷，需融入复古温暖感 |
| 7 | 虚拟投射不存储数据 | 加入 Dataset 表 + Delta Lake | 数据同步是本体查询的基础设施 |

---

## 附录 B：Palantir 参考来源

本文设计中关于 Palantir 架构的理解参考了以下公开资料：
- Palantir 本体工程核心思路与技术架构 (cnblogs.com/end/p/19144086)
- Palantir 本体论对智能体建设的价值 (cnblogs.com/end/p/19144102)
- Building with Palantir AIP: Logic Tools for RAG/OAG (blog.palantir.com)
- Palantir AIP Agent Studio 详解 (53ai.com)
- 业务逻辑即工具：Palantir 企业级 AI 助手 (modb.pro)
- Turning Conversation Into Action — Palantir CSE #2 (blog.palantir.com)
