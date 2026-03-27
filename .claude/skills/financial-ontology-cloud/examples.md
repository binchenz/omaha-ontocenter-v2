# Query Examples

## 1. List Available Objects

```bash
curl -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  http://69.5.23.70/api/public/v1/objects
```

## 2. List Bank Stocks

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Stock",
    "filters": {"industry": "银行"},
    "limit": 5
  }'
```

## 3. Search Stock by Name

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Stock",
    "filters": {"name": "平安"},
    "limit": 10
  }'
```

## 4. Query Financial Indicators (Raw Data)

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "FinancialIndicator",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 4
  }'
```

## 5. Query Financial Indicators (Formatted)

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "FinancialIndicator",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 4,
    "format": true
  }'
```

**Note:** `format: true` converts percentages (8.15 → 8.15%) and dates (20251231 → 2025-12-31)

## 6. Query Income Statement

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "IncomeStatement",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 4,
    "format": true
  }'
```

## 7. Query Balance Sheet

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "BalanceSheet",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 4,
    "format": true
  }'
```

## 8. Query Cash Flow

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "CashFlow",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 4,
    "format": true
  }'
```

## 9. Sort by Computed Property (Find Best ROE)

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "FinancialIndicator",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 5,
    "format": true,
    "order_by": "roe",
    "order": "desc"
  }'
```

## 10. Sort by List Date (Find Oldest Stocks)

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Stock",
    "filters": {"industry": "银行"},
    "limit": 10,
    "order_by": "list_date",
    "order": "asc"
  }'
```

## 11. Select Specific Fields (Reduce Data Transfer)

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Stock",
    "filters": {"industry": "银行"},
    "limit": 10,
    "select": ["ts_code", "name", "list_date"]
  }'
```

## 12. Combine Select + Format + Computed Properties

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "FinancialIndicator",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 5,
    "format": true,
    "select": ["end_date", "roe", "netprofit_margin", "financial_health_score"]
  }'
```
