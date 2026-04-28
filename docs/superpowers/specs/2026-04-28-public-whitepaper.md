# Omaha OntoCenter 白皮书

**An Open Source, AI-Native Alternative to Palantir Foundry for Small & Mid-Sized Enterprises**

> 版本：v1.0 · 发布日期：2026-04-28
> 仓库：[github.com/binchenz/omaha-ontocenter-v2](https://github.com/binchenz/omaha-ontocenter-v2)

---

## 1. 前言：为什么我们需要又一个数据平台？

### 1.1 中小企业的数据困境

在过去十年中，数据基础设施工具链经历了爆发式增长：从 Snowflake 到 dbt，从 Looker 到 Metabase，从 Airbyte 到 Fivetran。然而，对于绝大多数年营收 1 亿以下的中小企业（SME）而言，这些工具仍然太"重"：

- **dbt + Looker** 需要专职数据工程师，维护成本高昂
- **Metabase / Superset** 解决了可视化，但缺乏**业务语义层**，分析师仍要手写 SQL
- **Palantir Foundry** 是事实上的"业务对象 + AI"标杆，但它的商业授权对中小企业来说遥不可及（年费百万美元起）

中小企业的真实需求其实很朴素：

> "我有一个 Excel、一个 MySQL、一个第三方 API 接口。我想问业务问题——'上个月华东地区的高客单订单有多少'，得到答案。我不想学 SQL，不想配 ETL，也不想给数据工程师汇报。"

### 1.2 LLM 出现后的新可能

ChatGPT 之后，"自然语言 → SQL"的工具层出不穷（如 Vanna AI、SQL Chat）。但它们普遍存在两个根本性缺陷：

1. **缺乏业务语义**：直接将表结构喂给 LLM，模型不知道 `t_ord` 表是"订单"，`amt` 是"金额（元）"
2. **缺乏可控边界**：LLM 可能生成错误 SQL、跨权限查询、或编造不存在的字段

**Omaha OntoCenter 的核心命题**是：

> **构建一层介于"数据表"和"AI 助手"之间的本体（Ontology）**——
> 让业务人员定义"业务对象"和"对象关系"，LLM 在这层之上工作，既保留语义又约束行为。

这正是 Palantir Foundry 在企业数据领域的核心思想。我们的目标是：把这套思想以**开源、轻量、AI Native** 的方式带到中小企业。

---

## 2. 核心理念：Ontology-First 设计哲学

### 2.1 "业务对象" 而非 "数据表"

传统 BI 工具（Metabase、Superset）的世界观是**表**：
- 用户看到的是 `orders`、`customers`、`order_items` 等数据库表
- 想分析"客户复购率"，需要手写 JOIN

Omaha 的世界观是**业务对象**：
- 用户定义"订单（Order）"、"客户（Customer）"、"商品（Product）"
- 对象之间的关系（Link）是一等公民：`Customer.orders`、`Order.product`
- 分析"客户复购率"时，AI 知道这意味着遍历 `Customer → orders → 时间窗口聚合`

### 2.2 AI 作为查询代理，而非建模师

许多"AI 数据分析"产品试图让 LLM 自动建模——根据数据自动推断业务对象。我们的实践经验表明：

> **LLM 自动建模在简单场景下可用，在复杂业务下不可靠。**

因此，Omaha 采用**人在回路（Human-in-the-Loop）**的设计：
- LLM 提供**初稿**：扫描数据源后，建议本体定义（YAML）
- 用户**审核确认**：在 IDE 或 UI 中调整对象、字段、关系
- LLM 在确定的本体上工作：执行查询、聚合、导航

### 2.3 配置即代码（YAML-First）

本体定义采用 YAML 而非数据库表或 GUI：

```yaml
objects:
  - name: 订单
    slug: order
    source_entity: t_orders
    properties:
      - { name: order_id, slug: order_id, type: string, semantic_type: order_id }
      - { name: amount, slug: amount, type: number, semantic_type: currency_cny }
      - name: customer
        type: link
        link:
          target: Customer
          foreign_key: customer_id
          target_key: id
```

YAML 的优势：
- **可版本化**：本体变更可走 PR + Code Review 流程
- **可移植**：跨环境（dev/staging/prod）复用
- **AI 友好**：LLM 读写 YAML 比 GUI 操作更自然

---

## 3. 架构设计

### 3.1 整体分层

```
┌──────────────────────────────────────────────────────────┐
│  Frontend (React + TS)                                    │
│  · AssistantPage (Chat UI)                                │
│  · OntologyBrowser / OntologyGraph                        │
│  · DatasourcePage / PipelinesPage                         │
└────────────────────┬─────────────────────────────────────┘
                     │ REST + JWT
┌────────────────────▼─────────────────────────────────────┐
│  API Layer (FastAPI)                                      │
│  · /api/v1/chat        · /api/v1/ontology                 │
│  · /api/v1/projects    · /api/v1/query                    │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│  Agent Runtime                                            │
│  · ExecutorAgent (ReAct loop)                             │
│  · ProviderAdapter (DeepSeek/OpenAI/Anthropic)            │
│  · ConversationRuntime (history + system prompt)          │
└─────┬──────────────────────────────────────┬─────────────┘
      │                                       │
┌─────▼────────────────┐        ┌────────────▼────────────┐
│  Tool System         │        │  Ontology Layer         │
│  · ObjectTypeToolFactory      │  · OntologyStore         │
│  · ToolRegistryView           │  · LinkResolver          │
│  · BuiltinTools               │  · PathNavigator         │
│    (query/chart/modeling)     │  · ComputedPropertyEngine│
└──────────┬───────────┘        └────────────┬────────────┘
           │                                 │
           └────────────┬────────────────────┘
                        │
            ┌───────────▼──────────────┐
            │  Execution Layer         │
            │  · OmahaService          │
            │  · SemanticQueryBuilder  │
            │  · Connectors            │
            │    (SQL/CSV/MongoDB/REST)│
            └───────────┬──────────────┘
                        │
            ┌───────────▼──────────────────────────┐
            │ Data Sources                         │
            │ Tushare / PG / MySQL / Excel / CSV   │
            └──────────────────────────────────────┘
```

### 3.2 关键模块详解

#### **OntologyStore（本体持久化层）**
本体的"中央仓库"，负责：
- 对象（OntologyObject）和属性（ObjectProperty）的 CRUD
- **Slug 强制生成**：所有对象/属性的 ASCII 标识符自动从 `name` 生成（中文经 `pypinyin` 转拼音）
- 唯一性保证：tenant 范围内对象 slug 唯一，object 范围内属性 slug 唯一

**关键设计决策**：`create_object()` 完全忽略调用方传入的 `slug` 参数，强制使用 `slugify_name(name)`。这一防御性设计是我们交了"500 错误学费"换来的——任何上游漏掉 slug 生成都会被这一层兜底。

#### **LinkResolver / PathNavigator（关系导航层）**

`LinkResolver` 解析单跳 Link：

```python
# Product.category → Category
link = LinkResolver.resolve_link("Product", "category", ontology)
# → LinkDefinition(source="Product", target="Category",
#                  foreign_key="category_id", target_key="id")
```

`PathNavigator` 在 LinkResolver 上构建多跳导航：

```python
# Review → SKU → Category，过滤
PathNavigator.navigate({
    "start_object": "Review",
    "start_filters": {"id": "rev1"},
    "path": ["sku", "category"],
}, ontology, ctx)
```

这一抽象使得"客户的所有订单的所有商品的类目"这类问题，对 AI 来说就是一次 `navigate_path` 调用。

#### **ObjectTypeToolFactory（Per-Object 工具工厂）**

我们没有提供单一的 `query_data(table, filters)` 通用工具，而是**为每个对象动态生成专属工具**：

```
对象 Order → search_order, count_order, aggregate_order
对象 Customer → search_customer, count_customer, aggregate_customer
```

**为什么不用通用工具？**
- LLM 在选择具体工具时，**意图更明确**（OpenAI 官方推荐这种模式）
- 每个工具的 JSON Schema 可以**只暴露该对象的字段**，避免 LLM 编造不存在的字段
- 错误率显著降低（实测约 30% → < 5%）

**代价**：工具数量 = 对象数 × 3。对于 50+ 对象的项目，工具列表会很长。我们通过 `skill.allowed_tools` 白名单按场景裁剪。

#### **ExecutorAgent（ReAct 循环）**

标准的 think→act→observe→answer 循环：

```python
for _ in range(max_iterations):
    response = await provider.send(messages, tools)
    if not response.tool_calls:
        return final_answer(response.content)
    for tc in response.tool_calls:
        result = await registry.execute(tc.name, tc.arguments, ctx)
        runtime.append_tool_result(tc.id, result)
```

**亮点**：完整支持 DeepSeek thinking mode 的 `reasoning_content` 透传。这是我们踩过的另一个坑——DeepSeek 多轮对话要求把上一轮的 `reasoning_content` 原样回传，否则 400 错误。

#### **OmahaService（多数据源执行层）**

YAML 配置驱动的查询执行器：
- 解析 YAML 中的 `datasources` 段
- 根据对象的 `datasource_type`（sql/csv/mongodb/rest）选择 Connector
- 应用 `default_filters`、计算属性（ComputedProperty）、语义类型格式化（SemanticTypeFormatter）

### 3.3 数据流：一次完整查询

```
用户："华东地区上个月订单超过 1000 元的有多少？"
  │
  ▼
ChatServiceV2 → ConversationRuntime（注入本体上下文到 system prompt）
  │
  ▼
ExecutorAgent → DeepSeek Provider
  │
  ▼ LLM 决定调用工具
count_order(filters=[
  {field: "region",      op: "=",  value: "华东"},
  {field: "order_date",  op: ">=", value: "2026-03-01"},
  {field: "amount",      op: ">",  value: 1000}
])
  │
  ▼
ObjectTypeToolFactory 路由到 query_data → OmahaService
  │
  ▼
SemanticQueryBuilder 生成 SQL（应用 default_filters，避免全表扫描）
  │
  ▼
SQLConnector.execute() → 返回 count
  │
  ▼
ExecutorAgent 把结果交回 LLM
  │
  ▼
LLM 用业务语言回答："上个月华东地区订单超过 1000 元的有 326 笔。"
```

---

## 4. 关键技术决策

### 4.1 为什么 YAML 配置而非纯代码？

权衡过三种方案：
- **纯代码**：灵活但门槛高，业务人员无法参与
- **GUI 配置**：易用但不可版本化，难以审查
- **YAML 配置**：可读、可版本化、可被 LLM 生成和编辑

YAML 的最大优势是**可被 LLM 端到端处理**：从扫描数据源到生成本体草稿，整个建模流程都可以由 AI 辅助完成。

### 4.2 为什么 Per-Object 工具而非通用 SQL 工具？

| 维度 | 通用 query_sql | Per-Object 工具 |
|------|---------------|----------------|
| LLM 准确率 | 70%（容易 hallucinate 字段名） | 95%+（schema 严格约束） |
| 工具数量 | 1 | N × 3 |
| Token 消耗 | 低（一个 schema） | 中（N 个 schema） |
| 可控性 | 弱 | 强 |
| 安全性 | 弱（可能 DROP TABLE） | 强（白名单操作） |

我们选择牺牲少量 Token 换取**显著更高的可靠性和安全性**，这对于"业务用户自助分析"场景至关重要。

### 4.3 Slug 系统：一个工程细节的故事

OpenAI / DeepSeek 的工具名必须匹配 `^[a-zA-Z0-9_-]+$`。这意味着：
- 中文对象名"订单"不能直接做工具名
- 必须有一个 ASCII 别名（slug）

我们的 slug 生成规则：
1. 英文/数字/空格 → 转小写并连字符化（`Customer Order` → `customer-order`）
2. 中文 → 经 `pypinyin` 转拼音（`订单` → `ding-dan`）
3. 都不行 → fallback 到 `obj_<sha1[:8]>`

并且，`OntologyStore` 在创建对象时**强制重新生成 slug**，无视调用方传入的值。这是从一次生产 500 错误中提炼出的教训：任何允许"非法 slug"流入数据库的设计都是定时炸弹。

### 4.4 DeepSeek Thinking Mode 集成

DeepSeek 的 R1 系列模型在多轮对话中要求：
- 上一轮 `reasoning_content` 必须原样回传
- 否则 400 错误：`The 'reasoning_content' in the thinking mode must be passed back to the API`

我们在 `Message` dataclass 中添加 `reasoning_content` 字段，并在 `OpenAICompatAdapter` 全链路透传。这一支持让我们能用 DeepSeek-R1 的更强推理能力，成本仅为 GPT-4 的 1/30。

---

## 5. 同类品对比

### 5.1 vs Palantir Foundry

| 维度 | Palantir Foundry | Omaha OntoCenter |
|------|-----------------|------------------|
| 定位 | 企业级数据操作系统 | 中小企业数据分析平台 |
| 商业模式 | 商业，年费百万美元起 | 开源，MIT License |
| 本体（Ontology） | 一等公民，Object/Link/Action | 一等公民，Object/Link |
| AI 集成 | AIP（Artificial Intelligence Platform） | ReAct + DeepSeek |
| 部署 | 云 / 私有云（重） | Docker Compose / 单机（轻） |
| 数据源 | 企业级（SAP/Oracle/Hadoop） | 中小企业（MySQL/PG/Excel/REST） |
| 学习曲线 | 陡（需培训认证） | 缓（YAML + 自然语言） |
| 适用规模 | 大型企业（万人以上） | 中小企业（< 500 人） |

**我们不是 Foundry 的功能完整复刻**——Foundry 的 Pipeline、Foundry ML、Workshop、Slate 等模块远超本项目范围。我们专注于**最有价值的子集**：Ontology + AI Query。

### 5.2 vs Cube + Metabase

| 维度 | Cube + Metabase | Omaha OntoCenter |
|------|-----------------|------------------|
| 语义层 | Cube（schema as code） | YAML 本体 |
| BI 可视化 | Metabase（专业） | 内置 Chart Engine（轻量） |
| AI 查询 | 弱（需要 plugin） | 一等公民（ReAct + Tools） |
| 对象关系 | Join（SQL 风格） | Link（对象风格） |
| 上手难度 | 中（需懂 Cube schema） | 低（YAML + 中文 name） |

Cube + Metabase 是当前开源 BI 的事实标准组合。**Omaha 的差异**在于：
- **AI Native**：从设计第一天就以 LLM 为主要交互入口
- **业务对象视角**：Link 比 Join 更接近业务语言

### 5.3 vs DataHub / OpenMetadata

| 维度 | DataHub / OpenMetadata | Omaha OntoCenter |
|------|----------------------|------------------|
| 核心目的 | 元数据治理（lineage / catalog） | 可执行本体（query 落地） |
| 数据查询 | 不支持（只是目录） | 一等公民 |
| 业务语义 | 有（glossary） | 有（ontology） |
| AI 集成 | 弱 | 强 |

DataHub 是"**数据资产的目录**"，Omaha 是"**可被 AI 调用的业务本体**"。两者可以并存：DataHub 做数据治理，Omaha 做业务分析。

### 5.4 定位象限图

```
                  AI Native
                     ▲
                     │
     Vanna AI    ●   │   ●  Omaha OntoCenter ★
     SQL Chat        │
                     │
                     │
   ──────────────────┼──────────────────► 业务语义强度
                     │
   Metabase ●        │   ● Palantir Foundry
   Superset          │
                     │
   DataHub ●         │   ● Cube
                     │
                     ▼
              传统建模 / SQL-Centric
```

Omaha 位于"右上象限"——**强业务语义 + AI Native**，目前在开源世界这个象限是空的。

---

## 6. 优缺点诚实分析

### 6.1 优势

- **轻量易部署**：单机 Docker Compose 启动，10 分钟跑通
- **AI Native**：从架构层面集成 LLM，不是事后插件
- **配置驱动**：YAML 本体可版本化、可审查、可被 AI 编辑
- **业务对象视角**：Link 比 Join 更符合业务语言
- **多数据源**：原生支持 SQL/CSV/MongoDB/REST，跨源 Link 可用
- **开源 MIT**：商业友好，可二次开发

### 6.2 局限（v1.0 实事求是）

- **无流数据支持**：当前只支持批量查询，无 Kafka / Flink 集成
- **权限治理较弱**：仅有项目级 owner/member，无字段级 ACL
- **可视化建模未完成**：本体定义需手写 YAML 或调用 API，可视化编辑器在路线图中
- **规模有限**：单机部署，未做大规模压力测试（当前推荐 < 100 并发）
- **测试覆盖**：366 单元测试 + 部分集成测试，E2E 覆盖待加强
- **Agent 能力初级**：当前是单 Agent ReAct 循环，无 Action Memory、无多 Agent 协作
- **生态早期**：connector 数量有限，社区贡献者较少

### 6.3 不适用场景

- 大型企业（万人以上）需要 Foundry / Snowflake 这类重型平台
- 强事务场景（金融交易系统）需要专业 BI + 治理工具
- 实时分析（毫秒级）需要 ClickHouse / Druid
- 严监管场景（医疗 / 银行）需要更严格的审计和合规

---

## 7. 路线图

### 7.1 短期（Q2-Q3 2026）

**多数据源拓展**：
- MongoDB（已有基础 connector，待完善 Link 支持）
- Snowflake / BigQuery / ClickHouse
- Kafka（流数据初步支持）
- 私有 REST API 标准化

**可视化本体编辑器**（Foundry Workshop 风格）：
- 拖拽式定义 Object 和 Property
- 关系图谱可视化（已有基础 OntologyGraph 页面）
- 实时预览生成的 YAML
- LLM 辅助：导入数据源后自动生成本体草稿，用户在 GUI 中确认调整

### 7.2 中期（Q4 2026）

**Agent 能力深化**：
- **Action Memory**：跨会话记忆用户偏好（"该用户偏好按月聚合"）
- **多 Agent 协作**：Planner / Researcher / Visualizer 角色分离
- **Tool 自动选择优化**：当工具数 > 100 时的语义路由
- **本地化 LLM 支持**：Llama 3 / Qwen2 微调，在企业语料上训练
- **Sub-Agent**：复杂任务可由主 Agent 派发给子 Agent

**治理增强**：
- 字段级 ACL
- 审计日志完整化（已有 `audit_logs` 表，待完整接入）
- 数据脱敏规则

### 7.3 长期（2027+）

- **Action 系统**：本体上的"动作"（如"创建采购单"），不只是查询
- **Foundry Pipeline 风格的 ETL**：YAML 定义 transform，DAG 执行
- **企业知识图谱整合**：与 RAG / 文档检索打通
- **多租户 SaaS 模式**：托管版本

---

## 8. 结语：欢迎共建

Omaha OntoCenter 的目标不是"复刻 Foundry"，而是**让 Foundry 式的设计哲学触达更多组织**。我们认为：

> 数据分析的下一阶段，不是 BI 工具的功能堆砌，而是**业务本体 + AI 代理**的协同。

如果你也认同这个方向：

- **GitHub**: [omaha-ontocenter-v2](https://github.com/binchenz/omaha-ontocenter-v2)
- **License**: MIT
- **欢迎贡献**：
  - 新 connector（Snowflake / Kafka / 你的私有 API）
  - 行业本体模板（零售 / 制造 / SaaS）
  - 文档翻译（英文版本）
  - Bug 反馈和功能建议

**特别欢迎中小企业的真实使用反馈**——告诉我们你的数据长什么样，遇到了什么问题，我们会用项目演进来回应。

---

*本白皮书随项目演进持续更新。当前版本基于 v1.0（2026-04-28）实现状态撰写。*
