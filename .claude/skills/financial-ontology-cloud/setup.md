# Setup Guide

## API Access

The Omaha OntoCenter Cloud API is available at:
```
http://69.5.23.70/api/public/v1
```

## Authentication

Use the provided API token in the Authorization header:
```bash
Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM
```

## Optional: Set Environment Variable

For convenience, set the token as an environment variable:

```bash
export OMAHA_API_TOKEN="omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"
```

Add to `~/.zshrc` or `~/.bashrc` for persistence:
```bash
echo 'export OMAHA_API_TOKEN="omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"' >> ~/.zshrc
source ~/.zshrc
```

Then use in commands:
```bash
curl -H "Authorization: Bearer $OMAHA_API_TOKEN" \
  http://69.5.23.70/api/public/v1/objects
```

## Test Connection

```bash
curl -H "Authorization: Bearer omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM" \
  http://69.5.23.70/api/public/v1/objects
```

Expected response:
```json
{
  "objects": [
    {"object_type": "Stock", "description": "Stock information"},
    {"object_type": "FinancialIndicator", "description": "Financial indicators (ROE, ROA, margins, debt ratio)"}
  ]
}
```

## Rate Limits

- 100 queries per hour per API token
- HTTP 429 response when exceeded
