# Financial Ontology Query Examples

## Example 1: Basic Stock Query

**User Request:** "查找所有上市的银行股"

**Steps:**

1. List available objects (first time only):
```
mcp__omaha-ontocenter__list_objects
```

2. Get Stock schema to understand fields:
```
mcp__omaha-ontocenter__get_schema
{
  "object_type": "Stock"
}
```

3. Query bank stocks:
```
mcp__omaha-ontocenter__query_data
{
  "object_type": "Stock",
  "selected_columns": ["ts_code", "name", "industry", "market", "list_date"],
  "filters": [
    {"field": "industry", "operator": "=", "value": "银行"}
  ],
  "limit": 20
}
```

**Expected Result:**
- List of bank stocks with code, name, industry, market, and listing date
- Default filter automatically excludes delisted stocks

---

## Example 2: Financial Metrics Query

**User Request:** "平安银行的市盈率、ROE和净利润率"

**Steps:**

1. Query with join to FinancialIndicator:
```
mcp__omaha-ontocenter__query_data
{
  "object_type": "Stock",
  "selected_columns": ["ts_code", "name"],
  "joins": [
    {
      "object_type": "FinancialIndicator",
      "join_field": "ts_code",
      "selected_columns": ["pe", "roe", "net_profit_margin", "report_date"]
    }
  ],
  "filters": [
    {"field": "name", "operator": "like", "value": "%平安银行%"}
  ],
  "limit": 5
}
```

**Expected Result:**
- Stock info with financial metrics
- Semantic formatting: pe as ratio, roe/net_profit_margin as percentages

---

## Example 3: Multi-Stock Comparison

**User Request:** "对比工商银行、建设银行和农业银行的ROE和市盈率"

**Steps:**

1. Query multiple stocks with financial indicators:
```
mcp__omaha-ontocenter__query_data
{
  "object_type": "Stock",
  "selected_columns": ["ts_code", "name", "industry"],
  "joins": [
    {
      "object_type": "FinancialIndicator",
      "join_field": "ts_code",
      "selected_columns": ["pe", "roe", "report_date"]
    }
  ],
  "filters": [
    {
      "field": "name",
      "operator": "in",
      "value": ["工商银行", "建设银行", "农业银行"]
    }
  ],
  "limit": 10
}
```

**Expected Result:**
- Comparison table with all three banks
- Latest financial metrics for each

---

## Example 4: Filtered by Valuation

**User Request:** "找出市盈率低于15的银行股"

**Steps:**

1. Query with multiple filters:
```
mcp__omaha-ontocenter__query_data
{
  "object_type": "Stock",
  "selected_columns": ["ts_code", "name", "industry"],
  "joins": [
    {
      "object_type": "FinancialIndicator",
      "join_field": "ts_code",
      "selected_columns": ["pe", "pb", "roe"]
    }
  ],
  "filters": [
    {"field": "industry", "operator": "=", "value": "银行"},
    {"field": "FinancialIndicator.pe", "operator": "<", "value": 15}
  ],
  "limit": 20
}
```

**Expected Result:**
- Bank stocks with PE < 15
- Includes PB and ROE for context

---

## Example 5: Balance Sheet Analysis

**User Request:** "查看平安银行的资产负债表"

**Steps:**

1. Query balance sheet data:
```
mcp__omaha-ontocenter__query_data
{
  "object_type": "Stock",
  "selected_columns": ["ts_code", "name"],
  "joins": [
    {
      "object_type": "BalanceSheet",
      "join_field": "ts_code",
      "selected_columns": ["total_assets", "total_liabilities", "total_equity", "end_date"]
    }
  ],
  "filters": [
    {"field": "name", "operator": "like", "value": "%平安银行%"}
  ],
  "limit": 4
}
```

**Expected Result:**
- Balance sheet items with currency formatting
- Multiple periods if available

---

## Example 6: Save Query as Asset

**User Request:** "保存这个查询，命名为'银行股估值分析'"

**Steps:**

1. After running a query, save it:
```
mcp__omaha-ontocenter__save_asset
{
  "name": "银行股估值分析",
  "description": "市盈率低于15的银行股及其财务指标",
  "base_object": "Stock",
  "selected_columns": ["ts_code", "name", "industry"],
  "filters": [
    {"field": "industry", "operator": "=", "value": "银行"},
    {"field": "FinancialIndicator.pe", "operator": "<", "value": 15}
  ],
  "joins": [
    {
      "object_type": "FinancialIndicator",
      "join_field": "ts_code",
      "selected_columns": ["pe", "pb", "roe"]
    }
  ],
  "row_count": 12
}
```

2. List saved assets:
```
mcp__omaha-ontocenter__list_assets
```

**Expected Result:**
- Asset saved with ID
- Can be reused later

---

## Example 7: Complex Multi-Object Query

**User Request:** "找出ROE>15%且现金流为正的科技股"

**Steps:**

1. Query with multiple joins:
```
mcp__omaha-ontocenter__query_data
{
  "object_type": "Stock",
  "selected_columns": ["ts_code", "name", "industry"],
  "joins": [
    {
      "object_type": "FinancialIndicator",
      "join_field": "ts_code",
      "selected_columns": ["roe", "pe"]
    },
    {
      "object_type": "CashFlow",
      "join_field": "ts_code",
      "selected_columns": ["operating_cash_flow", "end_date"]
    }
  ],
  "filters": [
    {"field": "industry", "operator": "like", "value": "%科技%"},
    {"field": "FinancialIndicator.roe", "operator": ">", "value": 15},
    {"field": "CashFlow.operating_cash_flow", "operator": ">", "value": 0}
  ],
  "limit": 20
}
```

**Expected Result:**
- Tech stocks meeting both criteria
- Financial and cash flow metrics included
