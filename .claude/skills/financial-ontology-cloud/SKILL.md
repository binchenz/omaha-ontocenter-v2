# Financial Ontology Cloud API

Query financial data using the Omaha OntoCenter cloud API.

## Prerequisites

- API key from https://ontocenter.example.com
- Set `ONTOCENTER_API_KEY` environment variable

## Base URL

```
https://ontocenter.example.com/api/v1
```

**NOTE:** Replace `ontocenter.example.com` with the actual domain provided during setup.

## Available Objects

- `Stock` - Stock information and metrics
- `IncomeStatement` - Income statement data
- `BalanceSheet` - Balance sheet data
- `CashFlow` - Cash flow statement data

## Common Queries

List objects:
```bash
curl -H "X-API-Key: $ONTOCENTER_API_KEY" \
  https://ontocenter.example.com/api/v1/query/objects
```

Query stocks:
```bash
curl -H "X-API-Key: $ONTOCENTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"object_type": "Stock", "filters": {}}' \
  https://ontocenter.example.com/api/v1/query/execute
```

See `examples.md` for more query patterns.
