---
name: financial-ontology-cloud
description: This skill connects to a live Chinese A-share stock database. Reach for it whenever the user wants to fetch, check, or act on real stock data — not learn about finance. Covers: looking up a stock by name or code (茅台, 平安银行, 000001.SZ), checking valuation (PE/PB/估值), financial health (ROE/净利润率), technical signals (MACD/RSI/技术面), screening stocks by criteria (选股/筛选), and managing a watchlist (自选股 — viewing, adding, removing). If the user is asking "what is X" or wants Python/charts with no data fetch, skip it. Otherwise, use it.
---

# Financial Ontology Cloud API

Query financial data using the Omaha OntoCenter cloud API.

## Prerequisites

- API Token: `omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM`
- Set environment variable (optional): `export OMAHA_API_TOKEN="omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"`

## Base URL

```
http://69.5.23.70/api/public/v1
```

## Available Objects

- `Stock` - Stock information (ts_code, name, industry, area, list_date)
- `DailyQuote` - Daily OHLCV data (open, high, low, close, volume)
- `Industry` - Industry classification statistics
- `ValuationMetric` - Daily valuation metrics (PE, PB, market cap)
- `FinancialIndicator` - Financial indicators (ROE, ROA, profit margins, debt ratio)
- `IncomeStatement` - Income statement data (revenue, profit)
- `BalanceSheet` - Balance sheet data (assets, liabilities, equity)
- `CashFlow` - Cash flow statement data (operating, investing, financing cash flows)
- `Sector` - Sector/concept classification (AI, semiconductor, new energy)
- `SectorMember` - Sector membership (stock-sector relationships)
- `TechnicalIndicator` - Technical indicators (MA, MACD, RSI, KDJ)

## Common Queries

List available objects:
```bash
curl -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  http://69.5.23.70/api/public/v1/objects
```

Query stocks:
```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "Stock", "filters": {}, "limit": 10}'
```

Query financial indicators with formatting:
```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "filters": {"ts_code": "000001.SZ"}, "limit": 5, "format": true}'
```

Aggregate query (statistics):
```bash
curl -X POST http://69.5.23.70/api/public/v1/aggregate \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "DailyQuote", "filters": {"ts_code": "000001.SZ"}, "aggregations": [{"field": "close", "function": "avg"}, {"field": "close", "function": "max"}]}'
```

## Ontology Features

**Semantic Types**: Data is automatically formatted based on semantic types defined in the ontology:
- `percentage` - Formats as "8.15%"
- `currency_cny` - Formats as "¥59257.77亿"
- `date` - Formats as "2025-12-31"
- `ratio` - Formats as "6.70x" (PE, PB ratios)
- `growth_rate` - Formats as "+12.50%" or "-3.72%" (with sign)
- `score` - Formats as "20.3分" (composite scores)
- `multiplier` - Formats as "2.94倍" (PS, PCF ratios)

**Computed Properties**: Calculated fields defined in ontology (use `format: true` to see them):
- FinancialIndicator: `financial_health_score`, `profitability_score`, `leverage_ratio`, `dupont_roe`, `asset_efficiency`
- ValuationMetric: `market_cap_billion`, `free_float_ratio`
- TechnicalIndicator: `trend_score`, `ma_gap`
- BalanceSheet: `debt_to_asset_ratio`, `equity_ratio`, `current_ratio`
- CashFlow: `cash_change`, `total_cashflow`
- IncomeStatement: `profit_margin`, `operating_efficiency`

**Key Computed Properties Explained:**
- `dupont_roe`: DuPont ROE = Net Profit Margin × Asset Turnover × Equity Multiplier
- `financial_health_score`: Comprehensive score combining ROE and net profit margin
- `asset_efficiency`: Asset turnover rate as percentage
- `market_cap_billion`: Total market cap in billions (亿元)
- `free_float_ratio`: Percentage of shares that are freely tradable
- `trend_score`: Composite trend indicator combining MACD and RSI
- `ma_gap`: Short-term moving average deviation from long-term MA

**Default Filters**: Automatically applied from ontology (e.g., Stock queries exclude retired stocks)

**Business Context**: Available via schema endpoint for each object type

## Query Parameters

**Query Endpoint** (`/query`):
- `object_type` (required): Object type to query
- `filters` (optional): Filter conditions (e.g., `{"industry": "银行"}`). Supports operators for numeric/date fields:
  - Simple equality: `{"ts_code": "000001.SZ"}`
  - Comparison: `{"pct_chg": {"operator": ">", "value": 1}}`
  - Range: `{"trade_date": {"operator": ">=", "value": "20260101"}}`
  - List: `{"ts_code": {"operator": "in", "value": ["000001.SZ", "600036.SH"]}}`
  - Operators: `>`, `<`, `>=`, `<=`, `=`, `in`
- `limit` (optional): Result limit (default: 100, max: 1000)
- `offset` (optional): Result offset (default: 0)
- `format` (optional): Apply semantic formatting - percentages, currency, dates (default: false)
- `order_by` (optional): Field name to sort by (supports computed properties)
- `order` (optional): Sort order - "asc" or "desc" (default: "desc")
- `select` (optional): List of field names to return (default: all fields)

**Aggregate Endpoint** (`/aggregate`):
- `object_type` (required): Object type to query
- `filters` (optional): Filter conditions
- `aggregations` (required): List of aggregations, each with:
  - `field`: Field name to aggregate
  - `function`: Aggregation function - "count", "avg", "max", "min", "sum"

**Aggregate Functions**:
- `count`: Count non-null values
- `avg`: Average of numeric values
- `max`: Maximum value
- `min`: Minimum value
- `sum`: Sum of numeric values

**Example Aggregations**:
- Count stocks by industry: `{"object_type": "Stock", "filters": {"industry": "银行"}, "aggregations": [{"field": "ts_code", "function": "count"}]}`
- Average stock price: `{"object_type": "DailyQuote", "filters": {"ts_code": "000001.SZ"}, "aggregations": [{"field": "close", "function": "avg"}]}`
- Market cap statistics: `{"object_type": "ValuationMetric", "filters": {"ts_code": "000001.SZ"}, "aggregations": [{"field": "total_mv", "function": "avg"}, {"field": "total_mv", "function": "max"}]}`
- YTD price range: `{"object_type": "DailyQuote", "filters": {"ts_code": "000001.SZ", "trade_date": {"operator": ">=", "value": "20260101"}}, "aggregations": [{"field": "close", "function": "avg"}, {"field": "close", "function": "max"}, {"field": "close", "function": "min"}]}`

## Data Coverage

- **5,493 stocks** in the database (A-share market)
- Daily quotes, valuation metrics, technical indicators updated regularly
- Financial statements (quarterly/annual) for all listed companies
- 1,000+ sector/concept classifications

## Rate Limiting

- **Unlimited queries** - No rate limit restrictions
- Optimized for high-frequency data access

## Watchlist (自选股)

Manage a personal watchlist of stocks. All watchlist operations use the same API token.

**Get watchlist:**
```bash
curl -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  http://69.5.23.70/api/public/v1/watchlist
```

**Add stock to watchlist:**
```bash
curl -X POST http://69.5.23.70/api/public/v1/watchlist \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"ts_code": "000001.SZ", "note": "等待回调到10元"}'
```

**Remove stock from watchlist:**
```bash
curl -X DELETE http://69.5.23.70/api/public/v1/watchlist/{item_id} \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"
```

See `examples.md` for more query patterns.

## Practical Investment Scenarios

**场景1：查询自选股最新行情**
```bash
# 先获取自选股列表
curl -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  http://69.5.23.70/api/public/v1/watchlist

# 再查询某只股票最新5日行情
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "DailyQuote", "filters": {"ts_code": "000001.SZ"}, "limit": 5, "format": true, "order_by": "trade_date", "order": "desc"}'
```

**场景2：查询股票估值 + 技术面综合分析**
```bash
# 估值
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "ValuationMetric", "filters": {"ts_code": "600036.SH"}, "select": ["ts_code", "trade_date", "pe", "pb", "market_cap_billion"], "limit": 1, "format": true, "order_by": "trade_date", "order": "desc"}'

# 技术面
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "TechnicalIndicator", "filters": {"ts_code": "600036.SH"}, "select": ["ts_code", "trade_date", "close", "ma5", "ma20", "macd_signal", "rsi_signal", "trend_score"], "limit": 1, "format": true, "order_by": "trade_date", "order": "desc"}'
```

**场景3：查询公司三大报表**
```bash
# 利润表
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "IncomeStatement", "filters": {"ts_code": "000001.SZ"}, "select": ["ts_code", "end_date", "total_revenue", "n_income", "profit_margin"], "limit": 4, "format": true, "order_by": "end_date", "order": "desc"}'

# 资产负债表
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "BalanceSheet", "filters": {"ts_code": "000001.SZ"}, "select": ["ts_code", "end_date", "total_assets", "total_liab", "debt_to_asset_ratio", "equity_ratio"], "limit": 4, "format": true, "order_by": "end_date", "order": "desc"}'

# 现金流量表
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "CashFlow", "filters": {"ts_code": "000001.SZ"}, "select": ["ts_code", "end_date", "n_cashflow_act", "n_cashflow_inv_act", "cash_change", "total_cashflow"], "limit": 4, "format": true, "order_by": "end_date", "order": "desc"}'
```

**场景4：筛选高ROE低负债优质股**
```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "FinancialIndicator", "select": ["ts_code", "end_date", "roe", "netprofit_margin", "dupont_roe", "financial_health_score"], "limit": 10, "format": true, "order_by": "financial_health_score", "order": "desc"}'
```

**场景5：分页浏览所有股票**
```bash
# 第1页
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "Stock", "select": ["ts_code", "name", "industry", "area"], "limit": 20, "offset": 0}'

# 第2页
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "Stock", "select": ["ts_code", "name", "industry", "area"], "limit": 20, "offset": 20}'
```
