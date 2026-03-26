# 金融数据对象设计方案

**日期：** 2026-03-26
**状态：** 已批准
**作者：** Claude Sonnet 4.6

## 1. 项目概述

为 Omaha OntoCenter 设计一套完整的金融数据对象体系，基于 Tushare Pro 数据源，支持股票投资分析、行业研究、量化交易和财务分析四大场景。

## 2. 需求分析

### 2.1 分析场景

- **股票投资分析**：选股、估值、基本面分析
- **行业研究**：行业对比、板块轮动、产业链分析
- **量化交易**：回测策略、因子分析、风险管理
- **财务分析**：财报解读、盈利能力、现金流分析

### 2.2 数据范围

- **市场范围**：A 股市场（上交所、深交所）
- **时间粒度**：以日线数据为主，适合中长期分析
- **实施策略**：设计完整对象体系，分阶段实现

## 3. 设计方案对比

### 方案 A：按数据类型分层设计

**核心思路：** 按照数据的性质分层，每层独立设计对象

**对象结构：**
- 基础层：Stock（股票基本信息）
- 行情层：DailyQuote（日线行情）
- 财务层：FinancialReport（财务报表）、FinancialIndicator（财务指标）
- 分析层：TechnicalIndicator（技术指标）、ValuationMetric（估值指标）
- 行业层：Industry（行业）、Sector（板块）

**优点：** 数据边界清晰，每个对象职责单一
**缺点：** 查询时需要手动 JOIN 多个对象，配置复杂

### 方案 B：按业务场景设计

**核心思路：** 为每个分析场景设计一个聚合对象

**对象结构：**
- InvestmentStock：包含基本信息 + 行情 + 估值（用于投资分析）
- FinancialStock：包含基本信息 + 财报 + 指标（用于财务分析）
- IndustryAnalysis：行业 + 板块 + 成分股（用于行业研究）
- TradingStock：行情 + 技术指标 + 因子（用于量化交易）

**优点：** 查询简单，一个对象包含场景所需的所有数据
**缺点：** 对象臃肿，数据冗余，不够灵活

### 方案 C：混合设计（已选择）⭐

**核心思路：** 以 Stock 为中心，通过 relationships 连接各类数据对象

**对象结构：**
- 核心对象：Stock（股票基本信息）作为中心节点
- 关联对象：
  - DailyQuote（日线行情）
  - FinancialReport（财务报表）
  - FinancialIndicator（财务指标）
  - Industry（行业）
  - TechnicalIndicator（技术指标）

**优点：**
- 灵活性高：可以按需组合查询
- 符合 Omaha 的 ontology 设计理念
- 支持增量扩展：新增对象不影响现有结构
- 数据复用：同一份数据可用于多个场景

**缺点：**
- 需要配置 relationships
- 复杂查询需要多次 JOIN

**选择理由：**
1. 符合项目架构：Omaha OntoCenter 本身就是基于 ontology + relationships 设计的
2. 灵活性最高：可以根据不同分析需求灵活组合对象
3. 易于扩展：未来添加新的数据类型只需新增对象和关系
4. 分阶段实现：可以先实现核心对象，再逐步添加其他对象

## 4. 详细设计

### 4.1 核心对象：Stock（股票基本信息）

Stock 对象是整个金融数据体系的中心节点，包含股票的基本信息。

**对象定义：**
```yaml
- name: Stock
  datasource: tushare_pro
  api_name: stock_basic
  description: 股票基本信息
  default_filters:
    - field: list_status
      operator: "="
      value: "L"
  properties:
    - name: ts_code
      type: string
      description: 股票代码（如 000001.SZ）
    - name: symbol
      type: string
      description: 股票简称（如 000001）
    - name: name
      type: string
      description: 股票名称（如 平安银行）
    - name: area
      type: string
      description: 地域（如 深圳）
    - name: industry
      type: string
      description: 所属行业（如 银行）
    - name: market
      type: string
      description: 市场类型（主板/创业板/科创板）
    - name: list_date
      type: string
      description: 上市日期（YYYYMMDD）
    - name: list_status
      type: string
      description: 上市状态（L上市/D退市/P暂停上市）
```

**设计要点：**
- `ts_code` 作为主键，是连接其他对象的关键字段
- 包含基本的分类维度（地域、行业、市场）用于筛选和分组
- `default_filters` 默认只查询上市状态的股票，避免退市股票干扰
- Tushare API: `pro.stock_basic()`

### 4.2 关联对象设计

#### 4.2.1 DailyQuote（日线行情）

用于投资分析和量化交易，提供股票的日线行情数据。

**对象定义：**
```yaml
- name: DailyQuote
  datasource: tushare_pro
  api_name: daily
  description: 股票日线行情
  properties:
    - name: ts_code
      type: string
      description: 股票代码
    - name: trade_date
      type: string
      description: 交易日期（YYYYMMDD）
    - name: open
      type: number
      description: 开盘价
    - name: high
      type: number
      description: 最高价
    - name: low
      type: number
      description: 最低价
    - name: close
      type: number
      description: 收盘价
    - name: pre_close
      type: number
      description: 昨收价
    - name: change
      type: number
      description: 涨跌额
    - name: pct_chg
      type: number
      description: 涨跌幅（%）
    - name: vol
      type: number
      description: 成交量（手）
    - name: amount
      type: number
      description: 成交额（千元）
```

**设计要点：**
- 包含完整的 OHLC 数据（开高低收）
- 提供涨跌幅和成交量数据用于技术分析
- Tushare API: `pro.daily()`

#### 4.2.2 FinancialIndicator（财务指标）

用于财务分析，提供股票的关键财务指标数据。

**对象定义：**
```yaml
- name: FinancialIndicator
  datasource: tushare_pro
  api_name: fina_indicator
  description: 财务指标数据
  properties:
    - name: ts_code
      type: string
      description: 股票代码
    - name: end_date
      type: string
      description: 报告期（YYYYMMDD）
    - name: eps
      type: number
      description: 基本每股收益
    - name: roe
      type: number
      description: 净资产收益率（%）
    - name: roa
      type: number
      description: 总资产报酬率（%）
    - name: gross_margin
      type: number
      description: 销售毛利率（%）
    - name: debt_to_assets
      type: number
      description: 资产负债率（%）
    - name: current_ratio
      type: number
      description: 流动比率
    - name: quick_ratio
      type: number
      description: 速动比率
```

**设计要点：**
- 包含盈利能力指标（ROE、ROA、毛利率）
- 包含偿债能力指标（资产负债率、流动比率）
- 通过 `end_date` 字段支持多期对比
- Tushare API: `pro.fina_indicator()`

#### 4.2.3 Industry（行业）

用于行业研究，提供行业分类和统计信息。

**对象定义：**
```yaml
- name: Industry
  datasource: tushare_pro
  api_name: stock_basic
  description: 行业分类
  query: "SELECT DISTINCT industry as name, COUNT(*) as stock_count FROM stock_basic WHERE list_status='L' GROUP BY industry"
  properties:
    - name: name
      type: string
      description: 行业名称
    - name: stock_count
      type: number
      description: 该行业股票数量
```

**设计要点：**
- 使用自定义 SQL 查询聚合行业数据
- 提供行业内股票数量统计
- 可用于行业对比和板块分析

### 4.3 Relationships 设计

定义对象之间的关联关系，使得可以通过 JOIN 查询组合数据。

```yaml
relationships:
  # Stock -> DailyQuote (一对多)
  - name: stock_daily_quotes
    description: 股票的日线行情数据
    from_object: Stock
    to_object: DailyQuote
    type: one_to_many
    join_condition:
      from_field: ts_code
      to_field: ts_code

  # Stock -> FinancialIndicator (一对多)
  - name: stock_financial_indicators
    description: 股票的财务指标数据
    from_object: Stock
    to_object: FinancialIndicator
    type: one_to_many
    join_condition:
      from_field: ts_code
      to_field: ts_code

  # Stock -> Industry (多对一)
  - name: stock_industry
    description: 股票所属行业
    from_object: Stock
    to_object: Industry
    type: many_to_one
    join_condition:
      from_field: industry
      to_field: name
```

**设计要点：**
- Stock -> DailyQuote：一只股票有多条日线行情记录
- Stock -> FinancialIndicator：一只股票有多期财务指标
- Stock -> Industry：多只股票属于同一个行业

**使用示例：**
```yaml
# 查询某只股票及其最近的行情
object_type: Stock
filters:
  - field: ts_code
    value: "000001.SZ"
joins:
  - relationship_name: stock_daily_quotes
    join_type: LEFT
selected_columns:
  - Stock.name
  - DailyQuote.trade_date
  - DailyQuote.close
  - DailyQuote.pct_chg
```

## 5. 分阶段实现计划

### 阶段 1：基础数据层（P0 - 核心必需）

**目标：** 建立基础数据查询能力

**对象：**
- Stock（股票基本信息）
- DailyQuote（日线行情）
- Industry（行业分类）

**关系：**
- Stock -> DailyQuote
- Stock -> Industry

**能力：**
- 查询股票基本信息和行情数据
- 按行业筛选和分组
- 支持简单的投资分析（价格走势、涨跌幅）

**工作量：** 约 1-2 天

---

### 阶段 2：财务分析层（P1 - 重要）

**目标：** 支持深度财务分析

**新增对象：**
- FinancialIndicator（财务指标）
- FinancialReport（财务报表 - 资产负债表、利润表、现金流量表）

**新增关系：**
- Stock -> FinancialIndicator
- Stock -> FinancialReport

**能力：**
- 财务指标分析（ROE、负债率、盈利能力）
- 财报数据查询
- 基本面选股

**工作量：** 约 2-3 天

---

### 阶段 3：量化分析层（P2 - 增强）

**目标：** 支持量化交易和技术分析

**新增对象：**
- TechnicalIndicator（技术指标 - MA、MACD、RSI 等）
- ValuationMetric（估值指标 - PE、PB、PS 等）
- Sector（板块分类 - 概念板块、地域板块）

**新增关系：**
- Stock -> TechnicalIndicator
- Stock -> ValuationMetric
- Stock -> Sector

**能力：**
- 技术指标计算和查询
- 估值分析
- 板块轮动分析
- 量化因子构建

**工作量：** 约 3-4 天

---

**实施建议：** 先实现阶段 1，验证数据源和查询功能正常后，再逐步推进阶段 2 和 3。

## 6. 完整配置示例

以下是阶段 1 的完整 YAML 配置示例：

```yaml
datasources:
  - id: tushare_pro
    name: Tushare Pro API
    type: tushare
    connection:
      token: ${TUSHARE_TOKEN}

ontology:
  objects:
    # 核心对象
    - name: Stock
      datasource: tushare_pro
      api_name: stock_basic
      description: 股票基本信息
      default_filters:
        - field: list_status
          operator: "="
          value: "L"
      properties:
        - name: ts_code
          type: string
          description: 股票代码
        - name: symbol
          type: string
          description: 股票简称
        - name: name
          type: string
          description: 股票名称
        - name: industry
          type: string
          description: 所属行业
        - name: area
          type: string
          description: 地域
        - name: market
          type: string
          description: 市场类型
        - name: list_date
          type: string
          description: 上市日期

    # 日线行情
    - name: DailyQuote
      datasource: tushare_pro
      api_name: daily
      description: 日线行情数据
      properties:
        - name: ts_code
          type: string
          description: 股票代码
        - name: trade_date
          type: string
          description: 交易日期
        - name: open
          type: number
          description: 开盘价
        - name: high
          type: number
          description: 最高价
        - name: low
          type: number
          description: 最低价
        - name: close
          type: number
          description: 收盘价
        - name: pct_chg
          type: number
          description: 涨跌幅
        - name: vol
          type: number
          description: 成交量
        - name: amount
          type: number
          description: 成交额

    # 行业分类
    - name: Industry
      datasource: tushare_pro
      api_name: stock_basic
      description: 行业分类
      properties:
        - name: name
          type: string
          description: 行业名称
        - name: stock_count
          type: number
          description: 股票数量

  relationships:
    - name: stock_daily_quotes
      description: 股票的日线行情数据
      from_object: Stock
      to_object: DailyQuote
      type: one_to_many
      join_condition:
        from_field: ts_code
        to_field: ts_code

    - name: stock_industry
      description: 股票所属行业
      from_object: Stock
      to_object: Industry
      type: many_to_one
      join_condition:
        from_field: industry
        to_field: name
```

## 7. Tushare API 映射表

| 对象 | Tushare API | 说明 |
|------|-------------|------|
| Stock | `pro.stock_basic()` | 股票基本信息 |
| DailyQuote | `pro.daily()` | 日线行情 |
| FinancialIndicator | `pro.fina_indicator()` | 财务指标 |
| FinancialReport | `pro.income()`, `pro.balancesheet()`, `pro.cashflow()` | 财务报表 |
| TechnicalIndicator | 需要自行计算或使用第三方库 | 技术指标 |
| ValuationMetric | `pro.daily_basic()` | 估值指标（PE、PB等）|

## 8. 技术考虑

### 8.1 数据查询优化

- Tushare Pro 有积分限制，需要合理控制查询频率
- 建议添加缓存机制，避免重复查询相同数据
- 对于历史数据，可以考虑定期批量下载到本地数据库

### 8.2 错误处理

- Tushare API 可能返回空数据或超时，需要优雅处理
- 在 `_query_tushare` 方法中已实现基本错误处理
- 建议添加重试机制和日志记录

### 8.3 扩展性

- 设计支持增量添加新对象，不影响现有功能
- 可以轻松添加港股、美股数据源（需要不同的 API）
- 支持自定义计算字段（computed properties）

## 9. 测试计划

### 9.1 单元测试

- 测试 Stock 对象查询
- 测试 DailyQuote 对象查询
- 测试 relationships JOIN 查询
- 测试过滤条件和分页

### 9.2 集成测试

- 测试完整的查询流程
- 测试 Tushare API 连接
- 测试错误处理和边界情况

### 9.3 性能测试

- 测试大量数据查询的性能
- 测试并发查询的稳定性

## 10. 总结

本设计方案采用混合设计模式，以 Stock 为中心，通过 relationships 连接各类金融数据对象。该方案具有以下优势：

1. **灵活性高**：可以按需组合查询，满足不同分析场景
2. **易于扩展**：新增对象不影响现有结构
3. **符合架构**：与 Omaha OntoCenter 的设计理念一致
4. **分阶段实现**：可以逐步推进，降低实施风险

通过三个阶段的实施，最终将建立一个完整的金融数据分析体系，支持股票投资分析、行业研究、量化交易和财务分析四大场景。
