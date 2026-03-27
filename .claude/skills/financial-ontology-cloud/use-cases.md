# Ontology-Driven Financial Analysis Use Cases

## Use Case 1: Find Best Performing Quarters

**Goal**: Identify quarters with highest financial health score

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "FinancialIndicator",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 5,
    "format": true,
    "order_by": "financial_health_score",
    "order": "desc",
    "select": ["end_date", "roe", "netprofit_margin", "financial_health_score"]
  }'
```

**Ontology Value**:
- `financial_health_score`: Computed property combining ROE and net profit margin
- Automatic percentage formatting
- Sorted by computed property

## Use Case 2: DuPont Analysis

**Goal**: Analyze ROE components using DuPont framework

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "FinancialIndicator",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 4,
    "format": true,
    "select": ["end_date", "roe", "netprofit_margin", "assets_turn", "assets_to_eqt", "dupont_roe"]
  }'
```

**Ontology Value**:
- `dupont_roe`: Computed as Net Margin × Asset Turnover × Equity Multiplier
- Shows ROE decomposition for deeper analysis

## Use Case 3: Efficient Data Transfer

**Goal**: Get only essential metrics to reduce bandwidth

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "FinancialIndicator",
    "filters": {"ts_code": "000001.SZ"},
    "limit": 10,
    "format": true,
    "select": ["end_date", "roe", "financial_health_score"]
  }'
```

**Ontology Value**:
- Field selection reduces response size by 95%
- Still includes computed properties
- Formatted output ready for display

## Use Case 4: Find Oldest Listed Banks

**Goal**: Identify most established banks by listing date

```bash
curl -X POST http://69.5.23.70/api/public/v1/query \
  -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Stock",
    "filters": {"industry": "银行"},
    "order_by": "list_date",
    "order": "asc",
    "limit": 10,
    "select": ["ts_code", "name", "list_date", "area"]
  }'
```

**Ontology Value**:
- Default filter automatically excludes delisted stocks
- Sorted by listing date
- Clean, focused output

## Summary

Ontology-driven design provides:
- **Computed Properties**: Business logic in configuration
- **Semantic Formatting**: Automatic percentage/currency formatting
- **Default Filters**: Business rules applied automatically
- **Flexible Queries**: Combine filter + sort + select + format
- **Performance**: Field selection reduces data transfer

