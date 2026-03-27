# Ontology功能完整演示

## 1. 基础查询 - 查找银行股

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "Stock", "filters": {"industry": "银行"}, "limit": 5, "select": ["ts_code", "name", "area"]}'
```

**Ontology价值**: 自动应用默认过滤器（排除退市股票）

## 2. 语义格式化 - 财务指标

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 3, "format": true, "select": ["end_date", "roe", "netprofit_margin"]}'
```

**Ontology价值**: 自动格式化为百分比（8.15%）、货币（¥59257.77亿）

## 3. 计算属性 - DuPont ROE分析

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 3, "format": true, "select": ["end_date", "roe", "netprofit_margin", "assets_turn", "dupont_roe", "financial_health_score"]}'
```

**Ontology价值**:
- `dupont_roe` = 净利率 × 资产周转率 × 权益乘数
- `financial_health_score` = ROE × 0.5 + 净利率 × 0.5

## 4. 排序 - 找出最佳季度

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 5, "format": true, "order_by": "financial_health_score", "order": "desc", "select": ["end_date", "roe", "financial_health_score"]}'
```

**Ontology价值**: 支持按计算属性排序

## 5. 字段选择 - 减少95%带宽

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 10, "format": true, "select": ["end_date", "roe"]}'
```

**Ontology价值**: 只返回需要的字段，大幅减少数据传输

## 6. 聚合查询 - 统计分析

```bash
# 统计银行业股票数量
curl -X POST http://69.5.23.70/api/public/v1/aggregate \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "Stock", "filters": {"industry": "银行"}, "aggregations": [{"field": "ts_code", "function": "count"}]}'

# 平安银行股价统计
curl -X POST http://69.5.23.70/api/public/v1/aggregate \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "DailyQuote", "filters": {"ts_code": "000001.SZ"}, "aggregations": [{"field": "close", "function": "avg"}, {"field": "close", "function": "max"}, {"field": "close", "function": "min"}]}'
```

**Ontology价值**:
- 支持count、avg、max、min、sum聚合函数
- 跨所有11个对象类型

## 7. 技术指标 - 趋势分析

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "TechnicalIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 3, "format": true, "select": ["trade_date", "ma5", "ma20", "trend_score", "ma_gap"]}'
```

**Ontology价值**:
- `trend_score` = MACD能量柱 × 10 + (RSI - 50)
- `ma_gap` = (MA5 - MA20) / MA20 × 100

## 8. 估值指标 - 市值分析

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "ValuationMetric", "filters": {"ts_code": "000001.SZ", "trade_date": "20260326"}, "format": true, "select": ["trade_date", "pe", "pb", "total_mv", "market_cap_billion", "free_float_ratio"]}'
```

**Ontology价值**:
- `market_cap_billion` = 总市值 / 100000（转换为亿元）
- `free_float_ratio` = 流通股 / 总股本

## 总结

**Ontology核心价值**:
1. **配置驱动**: 所有业务逻辑在YAML中定义
2. **23个计算属性**: 跨7个对象的高级分析指标
3. **语义类型**: 自动格式化（百分比、货币、日期）
4. **默认过滤器**: 自动应用业务规则
5. **灵活查询**: 支持排序、选择、格式化、聚合
6. **无速率限制**: 支持高频数据访问
7. **11个对象**: 完整的金融数据覆盖
