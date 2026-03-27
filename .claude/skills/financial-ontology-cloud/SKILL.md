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
- `filters` (optional): Filter conditions (e.g., `{"industry": "银行"}`)
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

## Rate Limiting

- **Unlimited queries** - No rate limit restrictions
- Optimized for high-frequency data access

See `examples.md` for more query patterns.
