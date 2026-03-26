# Query Examples

## 1. List Bank Stocks

```bash
curl -X POST https://ontocenter.example.com/api/v1/query/execute \
  -H "X-API-Key: $ONTOCENTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Stock",
    "filters": {
      "industry": "银行"
    }
  }'
```

## 2. Search Stock by Name

```bash
curl -X POST https://ontocenter.example.com/api/v1/query/execute \
  -H "X-API-Key: $ONTOCENTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "object_type": "Stock",
    "filters": {
      "name": "平安"
    }
  }'
```

## 3. List Available Objects

```bash
curl https://ontocenter.example.com/api/v1/query/objects \
  -H "X-API-Key: $ONTOCENTER_API_KEY"
```
