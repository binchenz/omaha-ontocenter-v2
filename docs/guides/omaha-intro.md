# 用本体论构建 AI 可理解的业务知识库

## 背景：AI 理解业务的难题

当我们让 AI 回答"找出银行股中 ROE 最高的10只股票"时，AI 需要知道：

- "ROE"是什么？它是百分比还是绝对值？
- "银行股"怎么筛选？
- 结果应该怎么格式化？

传统做法要么写死 SQL，要么靠 Prompt 描述——前者不灵活，后者不稳定。

**本体论提供了第三种方式：给 AI 一张结构化的业务语义地图。**

---

## 什么是本体论（Ontology）

本体论是对某个领域中概念、属性及其关系的形式化描述。简单说：

- **数据库**告诉系统"数据怎么存"
- **本体论**告诉系统"数据是什么意思"

在 Omaha OntoCenter 中，本体论用 YAML 配置文件定义，例如：

```yaml
objects:
  - name: Stock
    description: A股基本信息
    properties:
      - name: roe
        type: float
        semantic_type: percentage   # 告诉 AI：这是百分比
        description: 净资产收益率   # 告诉 AI：这代表什么
      - name: industry
        type: string
        semantic_type: category
        description: 所属行业
```

这份配置让系统（和 AI）知道：`roe` 是一个百分比类型的财务指标，代表净资产收益率。

---

## Omaha OntoCenter 的设计

Omaha 是一个配置驱动的金融数据分析平台，核心思路是：

**YAML 配置 → 业务对象 → 多数据源查询 → 语义格式化 → 用户 / AI**

### 已定义的金融对象

| 对象 | 描述 | 典型字段 |
|------|------|---------|
| Stock | A股基本信息 | ts_code, name, industry, area |
| FinancialIndicator | 财务指标 | roe, roa, grossprofit_margin, netprofit_margin |
| ValuationMetric | 估值指标 | pe_ttm, pb, dv_ratio, total_mv |
| DailyQuote | 日行情 | close, open, high, low, vol, pct_chg |
| TechnicalIndicator | 技术指标 | ma5, ma20, macd, rsi, kdj_k |
| IncomeStatement | 利润表 | total_revenue, n_income |
| BalanceSheet | 资产负债表 | total_assets, total_liab |
| CashFlow | 现金流量表 | n_cashflow_act |

### 语义类型系统

每个字段可以标注语义类型，系统自动格式化输出：

| 语义类型 | 原始值 | 格式化后 |
|---------|--------|---------|
| percentage | 0.1589 | 15.89% |
| currency | 12300000000 | ¥123.0亿 |
| ratio | 8.5 | 8.5x |
| date | 20231231 | 2023-12-31 |

### 计算属性

对象可以定义基于其他字段计算的派生指标，例如：

```yaml
computed_properties:
  - name: financial_health_score
    expression: "roe * 0.4 + roa * 0.3 + (1 - debt_to_assets/100) * 0.3"
    description: 综合财务健康评分
```

系统通过拓扑排序自动处理依赖关系，确保计算顺序正确。

---

## AI 如何使用这套知识库

### 自然语言查询

用户在 Chat 界面输入：
> "找出银行股中 ROE 大于 15%、PE 小于 10 的股票，按 ROE 从高到低排列"

AI 通过 **Function Calling** 自动调用 `screen_stocks` 工具：

```json
{
  "stock_filters": [{"field": "industry", "operator": "=", "value": "银行"}],
  "metric_objects": [
    {
      "object": "FinancialIndicator",
      "columns": ["roe"],
      "filters": [{"field": "roe", "operator": ">=", "value": 15}]
    },
    {
      "object": "ValuationMetric",
      "columns": ["pe_ttm"],
      "filters": [{"field": "pe_ttm", "operator": "<", "value": 10}]
    }
  ],
  "sort_by": "roe",
  "sort_order": "desc"
}
```

返回格式化结果：

| 股票 | 行业 | ROE | PE |
|------|------|-----|----|
| 招商银行 | 银行 | 18.5% | 5.2x |
| 工商银行 | 银行 | 16.3% | 6.8x |

AI 没有"猜"——它依据本体定义知道 ROE 是百分比、PE 是倍数，知道如何构造查询。

### MCP 接口

Omaha 实现了 Model Context Protocol（MCP），AI 编程助手（如 Claude Code）可以直接连接：

```json
{
  "mcpServers": {
    "omaha": {
      "command": "python",
      "args": ["-m", "app.mcp.server"]
    }
  }
}
```

连接后，AI 可以调用 8 个工具：`list_objects`、`get_schema`、`query_data`、`screen_stocks` 等，直接在编程环境中查询金融数据。

---

## 可迁移性

这套设计不局限于金融领域。换一份 YAML 配置，就是一个新领域的 AI 知识库：

- **医疗**：药品 → 适应症 → 副作用，查询"副作用少的降压药"
- **供应链**：商品 → 供应商 → 库存，查询"库存低于安全线的商品"
- **学术**：论文 → 作者 → 引用，查询"某方向被引最多的论文"

核心思路不变：用结构化配置定义业务语义，让 AI 通过 Function Calling 精确操作数据。

---

## 技术栈

- **后端**：FastAPI + SQLAlchemy，支持 SQLite / MySQL / PostgreSQL / Tushare Pro
- **前端**：React 18 + TypeScript + Tailwind CSS
- **AI 集成**：DeepSeek LLM + Function Calling + MCP Server
- **配置**：YAML 驱动，零硬编码业务逻辑

---

## 总结

| 传统方案 | Omaha 方案 |
|---------|-----------|
| 写死 SQL，改需求改代码 | YAML 配置，改配置即可 |
| Prompt 描述，AI 可能猜错 | 本体定义，AI 有精确依据 |
| 格式化靠手工处理 | 语义类型自动格式化 |
| 单一数据源 | 多数据源统一接口 |
| AI 工具无法直接访问 | MCP 标准接口，任何兼容工具可用 |

**本体论 + 配置驱动 + MCP = 让 AI 真正理解你的业务领域。**
