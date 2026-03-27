# Ontology API 使用指南

## 快速开始

### 1. 基础查询

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "Stock", "filters": {"industry": "银行"}, "limit": 5}'
```

### 2. 格式化输出

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 3, "format": true}'
```

### 3. 计算属性

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 3, "format": true, "select": ["end_date", "roe", "dupont_roe", "financial_health_score"]}'
```

### 4. 排序

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "filters": {"ts_code": "000001.SZ"}, "order_by": "financial_health_score", "order": "desc", "limit": 5, "format": true}'
```

### 5. 聚合查询

```bash
curl -X POST http://69.5.23.70/api/public/v1/aggregate \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "DailyQuote", "filters": {"ts_code": "000001.SZ"}, "aggregations": [{"field": "close", "function": "avg"}, {"field": "close", "function": "max"}]}'
```

## 高级用例

### 投资组合分析

使用批量查询对比多个股票：

```python
# 见 test_batch_query.py
python test_batch_query.py
```

输出示例：
```
财务健康度对比分析
股票代码         报告期          ROE        净利率        健康评分         杜邦ROE
000001.SZ    2025-12-31   8.15%      32.43%     20.29%       6.97%
600036.SH    2025-09-30   9.13%      45.56%     27.35%       9.04%
601398.SH    2025-09-30   6.63%      42.48%     24.55%       5.35%
```

### DuPont ROE分析

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 4, "format": true, "select": ["end_date", "roe", "netprofit_margin", "assets_turn", "assets_to_eqt", "dupont_roe"]}'
```

### 技术指标趋势

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "TechnicalIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 5, "format": true, "select": ["trade_date", "ma5", "ma20", "trend_score", "ma_gap"]}'
```

## API端点

### GET /objects
列出所有可用对象类型

### GET /schema/{object_type}
获取对象的schema定义（字段、计算属性、业务上下文）

### POST /query
查询数据

参数：
- `object_type`: 对象类型
- `filters`: 过滤条件
- `limit`: 结果数量限制（默认100，最大1000）
- `offset`: 偏移量
- `format`: 是否格式化输出
- `order_by`: 排序字段
- `order`: 排序方向（asc/desc）
- `select`: 返回的字段列表

### POST /aggregate
聚合查询

参数：
- `object_type`: 对象类型
- `filters`: 过滤条件
- `aggregations`: 聚合函数列表
  - `field`: 字段名
  - `function`: 函数名（count, avg, max, min, sum）

## 对象类型

1. **Stock** - 股票基本信息
2. **DailyQuote** - 日线行情（含4个计算属性）
3. **Industry** - 行业分类
4. **ValuationMetric** - 估值指标（含2个计算属性）
5. **FinancialIndicator** - 财务指标（含5个计算属性）
6. **IncomeStatement** - 利润表（含2个计算属性）
7. **BalanceSheet** - 资产负债表（含3个计算属性）
8. **CashFlow** - 现金流量表（含2个计算属性）
9. **Sector** - 概念板块
10. **SectorMember** - 板块成分股
11. **TechnicalIndicator** - 技术指标（含2个计算属性）

## 计算属性清单

### DailyQuote
- `price_volatility`: 当日价格波动率
- `volume_amount_ratio`: 量价比
- `is_limit_up`: 是否涨停
- `is_limit_down`: 是否跌停

### ValuationMetric
- `market_cap_billion`: 总市值（亿元）
- `free_float_ratio`: 流通比例

### FinancialIndicator
- `financial_health_score`: 财务健康度评分
- `profitability_score`: 盈利能力评分
- `leverage_ratio`: 杠杆率
- `dupont_roe`: 杜邦ROE
- `asset_efficiency`: 资产使用效率

### TechnicalIndicator
- `trend_score`: 综合趋势评分
- `ma_gap`: 短期均线偏离度

### BalanceSheet
- `debt_to_asset_ratio`: 资产负债率
- `equity_ratio`: 股东权益比率
- `current_ratio`: 流动比率

### CashFlow
- `cash_change`: 现金净增加额
- `total_cashflow`: 三大活动现金流合计

### IncomeStatement
- `profit_margin`: 净利率
- `operating_margin`: 营业利润率

## 测试工具

- `test_all_computed_properties.py` - 测试所有计算属性
- `test_aggregate_api.py` - 测试聚合查询
- `test_batch_query.py` - 批量查询演示

## 性能优化

1. **字段选择**: 使用`select`参数只返回需要的字段，减少95%带宽
2. **无速率限制**: 支持高频数据访问
3. **批量查询**: 循环调用API查询多个股票
4. **缓存**: PostgreSQL缓存层

## 支持

- 文档: `docs/FINAL_ONTOLOGY_REPORT.md`
- 示例: `docs/ONTOLOGY_DEMO.md`
- Skill: `.claude/skills/financial-ontology-cloud/SKILL.md`
