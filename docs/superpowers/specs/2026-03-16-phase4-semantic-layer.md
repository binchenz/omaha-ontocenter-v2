# Phase 4: Semantic Layer Design Spec

**Date:** 2026-03-16
**Status:** Approved
**Author:** Brainstorming Session

---

## Overview

Phase 4 在现有 YAML-driven Ontology 基础上增加**语义层（Semantic Layer）**，通过可视化编辑器让技术人员和业务人员共同定义业务含义、计算字段和业务指标，并自动增强 MCP Server 和 Chat Agent 的上下文理解能力。

**核心目标：**
1. 让 Agent 不只知道"字段叫什么"，还知道"字段意味着什么"
2. 让业务人员通过拖拽和简单输入定义计算指标，无需写 SQL
3. 语义定义自动注入 MCP 工具上下文，提升 Agent 回答质量

**向后兼容：** 所有新增 YAML 字段（`semantic_type`、`description`、`business_context`、`computed`、`metrics`）均为可选，默认值为 None/空，现有配置无需修改。

---

## 背景：为什么需要语义层

Palantir Foundry 成功的核心是把**业务语言和数据库语言之间的映射关系**变成一等公民持久化存储。Agent 在回答问题前，会先遍历知识图谱理解业务上下文，然后再决定调用哪些工具。

当前项目的语义层只有第 1 层（字段映射），缺少：
- 字段的业务含义描述（Agent 理解问题的关键）
- 计算字段和派生指标（毛利率、增长率等）
- 关系的业务语义（不只是 JOIN 条件，还有业务含义）
- 业务基准和常见问题示例（让 Agent 更准确）

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              语义层编辑器（前端）                     │
│  对象列表 | 字段编辑区（拖拽/公式） | Agent预览       │
└──────────────────────┬──────────────────────────────┘
                       │ PUT /api/v1/projects/{id}/semantic
┌──────────────────────▼──────────────────────────────┐
│              omaha_config（扩展 YAML）               │
│  基础映射 + semantic_type + description +            │
│  computed properties + metrics                      │
└──────────────────────┬──────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌───────────────┐            ┌────────────────┐
│  Chat Agent   │            │   MCP Server   │
│  系统提示增强  │            │  get_schema    │
│  （语义上下文）│            │  返回语义信息   │
└───────────────┘            └────────────────┘
```

**核心原则：** 语义层存储在 YAML 中，前端编辑器是 YAML 的可视化表示，两者始终同步。YAML 通过 `PUT /api/v1/projects/{id}/semantic` 保存，后端负责读写，保留环境变量占位符（`${VAR_NAME}`）。

---

## YAML 扩展格式

### 公式语法规则

公式中引用的名称均为**属性名（property name）**，即 YAML 中定义的 `name` 字段，而非数据库列名（`column`）。`semantic.py` 负责在生成 SQL 时将属性名替换为对应的列名。

例：`formula: "(price - cost) / price"` → SQL: `(sale_price - cost_price) / sale_price`

支持的公式语法：
- 四则运算：`+ - * /`
- 比较运算：`> < >= <= = !=`
- 逻辑运算：`AND OR NOT`
- 条件表达式：`IF(condition, true_value, false_value)`
- 聚合函数：`SUM() AVG() COUNT() MAX() MIN()`（仅用于 metrics，不用于 computed properties）

公式验证：保存时后端验证所有引用的属性名存在于同一对象中，否则返回 400 错误。

### 1. 字段语义类型（Semantic Types）

```yaml
ontology:
  objects:
    - name: Product
      description: "商品对象，代表平台上销售的单个商品"  # 可选
      properties:
        - name: price
          column: sale_price
          type: decimal
          semantic_type: currency      # 可选，新增
          currency: CNY                # 仅 semantic_type=currency 时有效
          description: "商品售价"      # 可选

        - name: discount_rate
          column: discount
          type: decimal
          semantic_type: percentage    # 可选
          description: "折扣率"

        - name: status
          column: prd_status
          type: string
          semantic_type: enum          # 可选
          description: "商品上架状态"
          enum_values:                 # 仅 semantic_type=enum 时有效
            - value: "1"
              label: "在售"
            - value: "0"
              label: "下架"
```

支持的 semantic_type：`currency` | `percentage` | `enum` | `date` | `id` | `text` | `computed`

### 2. 计算字段（Computed Properties）

计算字段不对应数据库列，由 `semantic.py` 在查询时展开为 SQL 子表达式。

```yaml
        - name: gross_margin
          semantic_type: computed      # 无 column 字段
          formula: "(price - cost) / price"   # 引用属性名
          return_type: percentage
          description: "商品毛利率，反映单品盈利能力"
          business_context: "毛利率 > 30% 视为健康，< 10% 需要关注"

        - name: is_high_value
          semantic_type: computed
          formula: "IF(price > 1000 AND sales_count > 100, true, false)"
          return_type: boolean
          description: "高价值商品标识"
          business_context: "价格超过1000且销量超过100件的商品"
```

### 3. 关系语义增强

```yaml
  relationships:
    - name: product_to_category
      from_object: Product
      to_object: Category
      type: many_to_one
      join_condition:
        from_field: category_id
        to_field: id
      description: "商品所属的销售类目，用于分类分析和定价策略"  # 编辑器强制填写
```

### 4. 业务指标（Metrics）

Metrics 使用聚合函数，`group_by` 引用**属性名**（非关系名）。如需按关联对象字段分组，需先在当前对象定义该字段（通过 JOIN 引入）。

```yaml
  metrics:                             # 顶层，与 objects 同级
    - name: total_revenue
      label: "总收入"
      description: "所有在售商品的总销售额"
      object: Product
      formula: "SUM(price * sales_count)"
      filters:
        - field: status
          value: "1"

    - name: avg_margin_by_category
      label: "分类平均毛利率"
      description: "按商品类目分组的平均毛利率"
      object: Product
      formula: "AVG(gross_margin)"     # 可引用 computed property
      group_by: category_name          # 引用属性名（非关系名）
```

---

## API 接口

### 语义层读写

```
GET  /api/v1/projects/{project_id}/semantic
     Response: { "config": "<yaml_string>", "parsed": { objects, metrics } }

PUT  /api/v1/projects/{project_id}/semantic
     Request:  { "config": "<yaml_string>" }
     Response: { "success": true } | { "error": "..." }
     说明: 后端验证 YAML 格式和公式引用，保留 ${VAR_NAME} 占位符原样写回
```

### 公式测试

```
POST /api/v1/projects/{project_id}/semantic/test-formula
     Request:  { "object_type": "Product", "formula": "(price - cost) / price", "return_type": "percentage" }
     Response: { "sql": "SELECT (sale_price - cost_price) / sale_price FROM ...", "sample": [0.342, 0.28, ...], "error": null }
     说明: LIMIT 100 行，超时 5s
```

### get_schema 增强响应

```json
{
  "success": true,
  "object_type": "Product",
  "description": "商品对象，代表平台上销售的单个商品",
  "columns": [
    { "name": "price", "type": "decimal", "semantic_type": "currency", "currency": "CNY", "description": "商品售价" },
    { "name": "gross_margin", "type": "computed", "formula": "(price - cost) / price", "return_type": "percentage", "description": "商品毛利率", "business_context": "毛利率 > 30% 视为健康" }
  ],
  "relationships": [
    { "name": "product_to_category", "to": "Category", "type": "many_to_one", "description": "商品所属销售类目，用于分类分析和定价策略" }
  ]
}
```

---

## 端到端示例：计算字段完整流程

**用户定义：** `gross_margin = (price - cost) / price`（属性名）

**semantic.py 展开：**
```sql
-- price → sale_price, cost → cost_price（按 column 映射替换）
SELECT product_id, (sale_price - cost_price) / sale_price AS gross_margin
FROM dm_ppy_product_info_ymd
LIMIT 100
```

**Agent 收到问题：** "毛利率最高的商品是哪个？"

**Agent 系统提示中包含：**
```
Product.gross_margin: 毛利率 = (price - cost) / price，>30%健康，<10%需关注
```

**Agent 调用 query_data：**
```json
{ "object_type": "Product", "selected_columns": ["Product.name", "Product.gross_margin"], "limit": 10 }
```

**semantic.py 生成 SQL：**
```sql
SELECT prd_name, (sale_price - cost_price) / sale_price AS gross_margin
FROM dm_ppy_product_info_ymd
ORDER BY gross_margin DESC
LIMIT 10
```

**Agent 返回：** "毛利率最高的商品是 XX，毛利率为 45.2%"

---

## 前端编辑器设计

### 整体布局（三栏式）

```
┌─────────────────────────────────────────────────────────┐
│  项目: 拼便宜  >  语义层编辑器              [保存] [测试] │
├──────────────┬──────────────────────────┬───────────────┤
│              │                          │               │
│  对象列表    │    字段编辑区             │  Agent预览    │
│              │                          │               │
│  📦 Product  │  ┌─ 基础字段 ──────────┐ │  实时展示     │
│  📦 Category │  │ price    [货币▼]    │ │  Agent能看到  │
│  📦 Order    │  │ cost     [货币▼]    │ │  的上下文     │
│              │  │ status   [枚举▼]    │ │               │
│  + 新建对象  │  └────────────────────┘ │               │
│              │  ┌─ 计算字段 ──────────┐ │               │
│              │  │ gross_margin  [fx] │ │               │
│              │  │ + 添加计算字段      │ │               │
│              │  └────────────────────┘ │               │
│              │  ┌─ 业务指标 ──────────┐ │               │
│              │  │ total_revenue  [∑] │ │               │
│              │  │ + 添加指标          │ │               │
│              │  └────────────────────┘ │               │
└──────────────┴──────────────────────────┴───────────────┘
```

**保存机制：** 点击"保存"按钮触发 `PUT /semantic`，非实时保存（避免部分状态写入）。编辑中有未保存变更时显示提示。

### FormulaBuilder 组件接口

```typescript
interface FormulaBuilderProps {
  objectType: string;           // 当前对象名，用于获取可用属性列表
  availableProperties: Property[]; // 可拖拽的属性列表（排除 computed）
  value: string;                // 当前公式字符串
  onChange: (formula: string) => void;
  onTest: (formula: string) => Promise<FormulaTestResult>; // 调用 test-formula API
}

interface FormulaTestResult {
  sql: string;
  sample: any[];
  error: string | null;
}
```

### 计算字段编辑器（弹窗）

```
┌─────────────────────────────────────────────────────┐
│  新建计算字段                                         │
│                                                     │
│  字段名称:  [gross_margin        ]                  │
│  显示名称:  [毛利率               ]                  │
│  业务描述:  [反映单品盈利能力      ] ← 必填           │
│  业务基准:  [>30%健康，<10%需关注  ] ← 可选           │
│                                                     │
│  公式构建器:                                         │
│  ┌─────────────────────────────────────────────┐   │
│  │  ( [price ▼] - [cost ▼] ) / [price ▼]      │   │
│  │                                             │   │
│  │  可用字段: price  cost  sales_count  ...    │   │
│  │  运算符:   + - * /  >  <  AND  OR  IF       │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  返回类型:  [百分比 ▼]                              │
│  SQL预览:   SELECT (sale_price-cost_price)/sale_price│
│  测试结果:  [0.342, 0.28, 0.41, ...]  ✅ (LIMIT 100)│
│                                                     │
│                    [取消]  [保存]                    │
└─────────────────────────────────────────────────────┘
```

### 关系编辑器

```
┌─────────────────────────────────────────────────────┐
│  Product  →  [多对一 ▼]  →  Category                │
│  关联条件:  Product.category_id = Category.id       │
│  业务描述:  [商品所属销售类目，用于分类分析和定价]   │ ← 必填
│                    [取消]  [保存]                    │
└─────────────────────────────────────────────────────┘
```

### Agent 上下文预览（右栏）

```
Product 对象的 Agent 上下文：
─────────────────────────────
商品对象，代表平台上销售的单个商品

字段：
• price (货币, CNY): 商品售价
• gross_margin (计算): 毛利率，反映单品盈利能力
  公式: (price - cost) / price
  基准: >30% 健康，<10% 需关注

关系：
• → Category (多对一): 商品所属销售类目，
  用于分类分析和定价策略

可回答的问题示例：
✓ "毛利率最高的商品是哪个？"
✓ "哪些类目的平均毛利率低于10%？"
✓ "在售商品的总收入是多少？"
```

---

## 语义层对 Agent 的增强

### Chat Agent 系统提示增强

`ChatService._build_ontology_context()` 扩展为包含语义信息：

```
当前项目数据对象：

Product（商品对象，代表平台上销售的单个商品）
  字段：
  - price: 商品售价（货币，CNY）
  - gross_margin [计算]: 毛利率 = (price-cost)/price，>30%健康，<10%需关注
  - status: 在售(1) / 下架(0)
  关系：
  - 属于 Category（用于分类分析和定价策略）

业务指标：
  - total_revenue: 所有在售商品总销售额 = SUM(price * sales_count)
  - avg_margin_by_category: 按类目分组的平均毛利率
```

### MCP Server get_schema 增强

`get_schema` 工具返回完整语义信息（见 API 接口章节），外部 Agent（Claude Desktop）也能获得业务上下文。

---

## 新增文件

```
backend/app/services/semantic.py          # 语义层解析、公式展开、SQL 生成
backend/app/api/semantic.py               # GET/PUT /semantic, POST /test-formula
frontend/src/pages/SemanticEditor.tsx     # 三栏式编辑器主页面
frontend/src/components/semantic/
  ObjectList.tsx                          # 左栏：对象列表
  PropertyEditor.tsx                      # 中栏：字段编辑区
  FormulaBuilder.tsx                      # 计算字段公式构建器
  AgentPreview.tsx                        # 右栏：Agent 上下文预览
  RelationshipEditor.tsx                  # 关系编辑弹窗
  MetricEditor.tsx                        # 业务指标编辑弹窗
frontend/src/services/semanticApi.ts      # 语义层 API 服务
```

---

## 修改文件

```
backend/app/services/omaha.py             # 解析扩展 YAML，computed 字段展开为 SQL
backend/app/services/chat.py              # _build_ontology_context() 注入语义信息
backend/app/mcp/tools.py                  # get_schema 返回完整语义信息
backend/app/api/__init__.py               # 注册 semantic router
frontend/src/App.tsx                      # 新增路由 /projects/:id/semantic
frontend/src/pages/ProjectDetail.tsx      # 新增"语义层"入口按钮
```

---

## Success Criteria

- [ ] 所有新增 YAML 字段为可选，现有配置不受影响
- [ ] 技术人员可通过编辑器定义字段语义类型（货币/百分比/枚举）
- [ ] 业务人员可通过公式构建器定义计算字段，无需写 SQL
- [ ] 公式支持四则运算、比较运算、逻辑运算、IF 条件
- [ ] 公式测试在 5s 内返回结果（LIMIT 100 行）
- [ ] 公式引用不存在的属性时，保存返回明确错误信息
- [ ] 关系定义强制填写业务描述
- [ ] Agent 预览实时展示语义上下文
- [ ] Chat Agent 能正确回答涉及计算字段的问题：
  - 输入："毛利率最高的商品是哪个？"
  - 期望 SQL 包含：`(sale_price - cost_price) / sale_price AS gross_margin`
  - 期望返回：商品名 + 毛利率数值
- [ ] MCP Server get_schema 返回完整语义信息（含 description、business_context）
- [ ] 编辑器点击"保存"后 YAML 写回，环境变量占位符保留

---

## Out of Scope (Phase 5+)

- 跨数据源对象合并（Employee 跨 HR + Finance 系统）
- 语义层版本控制和变更历史
- 字段级行级权限控制
- 自动推断语义类型（ML 辅助）
- 指标告警和监控
- group_by 关联对象字段（当前只支持当前对象属性）

