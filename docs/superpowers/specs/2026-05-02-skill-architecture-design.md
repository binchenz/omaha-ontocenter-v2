# V3 Skill 架构改造 — 设计文档

**日期**: 2026-05-02
**目标**: 将 v3 Agent 从 Tool-only 改为 Claude Code 风格的 Skill 系统，让不懂技术的老板只通过 Chat 对话就能完成数据分析全流程

---

## 背景

v3 当前要求用户手动完成：上传文件 → 看懂 schema → 编辑 YAML → 创建本体 → 去 Chat 提问。不懂技术的老板走不完这个流程。

改造后：老板在 Chat 里拖入 Excel 或直接提问，Agent 自主完成所有中间步骤。

## 核心决策

- **Skill 架构**: Claude Code 风格 — SKILL.md 定义工作流，内部调用 Tool 完成原子操作
- **全对话驱动**: 老板只和 Chat 交互，Agent 自动处理数据接入
- **轻量确认**: Agent 用大白话描述 schema 让用户确认，不展示技术细节
- **数据持久化**: 上传的文件自动存为平台数据源，以后可反复查询
- **单一界面**: 所有人看同一个界面，技术细节默认折叠，想看的人自己展开
- **Python 零改动**: 所有新代码在 Next.js，Python 只提供已有的数据 API

---

## 一、Skill 定义

每个 Skill 是一个目录，包含 SKILL.md：

```yaml
---
name: data-ingest
description: 用户上传文件或提到新数据时触发
triggers:
  - 上传文件（Excel/CSV）
  - "帮我分析这个"
  - "导入数据"
---

# 步骤
1. 接收用户上传的文件，调用 ingest_file 工具
2. 拿到 schema 后，用中文向用户描述列名和类型，问"对吗？"
3. 用户确认后，调用 create_ontology 工具
4. 完成后告诉用户"数据已就绪，你想了解什么？"

# 注意
- 不要展示 YAML 或技术术语
- 列类型用"金额""日期""文字"等大白话
- 如果用户说某列理解错了，修正后重新创建
```

### 四个 Skills

| Skill | 触发场景 | 内部调用的 Tools |
|---|---|---|
| data-ingest | 上传文件、提到新数据 | ingest_file, create_ontology |
| data-query | 提问已有数据 | list_my_data, search_*, aggregate_* |
| data-explore | "有什么数据？""能分析什么？" | list_my_data |
| general-chat | 闲聊、问候、与数据无关的问题 | 无 Tool |

---

## 二、Skill 引擎架构

### 两阶段加载

```
阶段 1: 路由（每次请求，轻量）
  → 读所有 SKILL.md 的 frontmatter（name + description + triggers）
  → 注入 system prompt
  → LLM 输出 "activate: data-ingest"

阶段 2: 执行（按需，完整）
  → 加载 data-ingest/SKILL.md 完整内容
  → 追加到 system prompt
  → LLM 按步骤执行，调用 Tool
```

### Skill 与 Tool 的关系

Skill 定义"做什么、按什么顺序"。Tool 执行"具体怎么做"。

Skill 本身就是 plan — 不需要额外的 Planner LLM 调用。现有的 planner.ts 删除。

### 执行流程变化

现有:
```
消息 → generatePlan (LLM) → loadAllTools → executeReactStream (LLM + tools)
```

改为:
```
消息 → skillRouter (LLM 选 skill) → loadSkill → executeWithSkill (LLM 按 skill 步骤 + tools)
```

---

## 三、新增 Tools（TypeScript 侧）

三个新 Tool 是现有 Python API 的 TypeScript 包装，不需要 Python 新增端点：

| Tool | 做什么 | 调用的已有 API |
|---|---|---|
| ingest_file | 上传文件 + 解析 schema | POST /ingest |
| create_ontology | 用推断结果生成 YAML + 创建本体 | POST /ontology |
| list_my_data | 列出用户已有的数据源和本体 | GET /ontology + GET /datasources |

---

## 四、Chat 前端改造

### 文件上传

Chat 输入框旁加文件拖拽/选择区。用户拖入文件后，Agent 的 data-ingest skill 接管。

用户看到的交互:
```
[用户拖入 "销售数据.xlsx"]
Agent: "收到文件，正在解析..."
Agent: "我看到这个表有 5 列：
  · 订单号（编号）
  · 客户名（文字）
  · 金额（元）
  · 状态（分类：已发货/待处理/延迟）
  · 日期
  对吗？"
用户: "对"
Agent: "数据已就绪（156 条记录）。你想了解什么？"
```

### 渐进式信息披露

默认（老板视角）:
```
Agent: "共 156 笔订单，总金额 ¥2,340,000，其中延迟订单占 23%..."
```

点击展开（技术视角）:
```
▸ 技能: data-query
▸ 调用: aggregate_order({measures: ["SUM(amount)"], group_by: ["status"]})
▸ 返回: 3 rows, 282ms
▸ [查看原始 OAG 响应]
```

### Skill 状态提示

轻量状态文字，不展示 skill 名称:
```
[正在解析文件...]        ← data-ingest
[正在查询数据...]        ← data-query
[思考中...]              ← general-chat
```

---

## 五、文件结构

```
v3/nextjs/src/
├── skills/                        ← 新增：Skill 定义
│   ├── data-ingest/SKILL.md
│   ├── data-query/SKILL.md
│   ├── data-explore/SKILL.md
│   └── general-chat/SKILL.md
├── app/agent/
│   ├── skill-router.ts            ← 新增：读 frontmatter，LLM 选 skill
│   ├── skill-loader.ts            ← 新增：加载完整 SKILL.md
│   ├── react.ts                   ← 保留：LLM + Tool calling 执行
│   ├── tool-registry.ts           ← 修改：加 3 个新 Tool
│   └── planner.ts                 ← 删除：Skill 替代 Planner
├── app/api/chat/sessions/[id]/
│   └── send/route.ts              ← 重写：skillRouter → loadSkill → execute
└── app/(app)/chat/
    └── page.tsx                   ← 修改：加文件上传 + 折叠详情

v3/python-api/                     ← 零改动
```

---

## 六、改动范围

| 模块 | 改动 | 大小 |
|---|---|---|
| Next.js 新增 | skills/ 目录 (4 个 SKILL.md) + skill-router.ts + skill-loader.ts | 中 |
| Next.js 修改 | tool-registry.ts (加 3 个 Tool) + send/route.ts (重写) + chat/page.tsx (文件上传 + 折叠详情) | 大 |
| Next.js 删除 | planner.ts | 删 |
| Python | 零改动 | 无 |

### 不改的

- 本体管理页面、数据源管理页面、Skills/能力中心页面
- OAG 查询引擎、MCP Runtime、Delta Lake / DuckDB
- 登录/认证
