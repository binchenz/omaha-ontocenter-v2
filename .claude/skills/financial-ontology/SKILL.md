---
name: financial-ontology
description: Query financial data using Omaha OntoCenter's ontology system via MCP
---

# Financial Ontology Query Skill

## Overview

This skill helps you query financial data (stocks, financial indicators, balance sheets, cash flows) using the Omaha OntoCenter ontology system through MCP tools.

## When to Use

Use this skill when:
- User asks to query stock information, financial data, or market analysis
- Need to explore available business objects and their schemas
- Want to filter, join, or aggregate financial data
- Need to save query results as reusable assets

## Prerequisites

**MCP Server must be configured.** Add to your `~/.claude/settings/mcp.json`:

```json
{
  "mcpServers": {
    "omaha-ontocenter": {
      "command": "python",
      "args": ["-m", "app.mcp.server"],
      "cwd": "/path/to/omaha_ontocenter/backend",
      "env": {
        "OMAHA_API_KEY": "your_api_key_here",
        "DATABASE_URL": "sqlite:///./omaha.db",
        "SECRET_KEY": "your_secret_key"
      }
    }
  }
}
```

**Get your API key:**
1. Start the backend server
2. Login to the web UI
3. Create a project and generate an API key
4. Copy the key to the MCP config above

## Available MCP Tools

- `list_objects` - List all available business objects
- `get_schema` - Get field definitions for an object (with semantic types)
- `get_relationships` - Get available joins between objects
- `query_data` - Execute queries with filters and joins
- `save_asset` - Save query results as a named asset
- `list_assets` - List saved assets
- `get_lineage` - View data lineage for an asset

## Workflow

### 1. Explore Available Objects

Always start by listing objects to understand what's available:

```
Use mcp__omaha-ontocenter__list_objects to see all business objects
```

Common objects:
- `Stock` - Basic stock information
- `FinancialIndicator` - Financial metrics (P/E, ROE, etc.)
- `BalanceSheet` - Balance sheet data
- `CashFlow` - Cash flow statements
- `IncomeStatement` - Income statement data

### 2. Understand Object Schema

Before querying, check the schema to see available fields and their semantic types:

```
Use mcp__omaha-ontocenter__get_schema with object_type="Stock"
```

Pay attention to:
- **Field names** - What columns are available
- **Semantic types** - How data is formatted (currency, percentage, date, etc.)
- **Computed properties** - Calculated fields (like valuation metrics)
- **Default filters** - Auto-applied filters (e.g., only listed stocks)

### 3. Query Data

Execute queries with filters and field selection:

```json
{
  "object_type": "Stock",
  "selected_columns": ["ts_code", "name", "industry", "market"],
  "filters": [
    {"field": "industry", "operator": "=", "value": "银行"}
  ],
  "limit": 10
}
```

**Filter operators:** `=`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `like`

### 4. Join Related Objects

Query multiple objects together using relationships:

```json
{
  "object_type": "Stock",
  "selected_columns": ["ts_code", "name"],
  "joins": [
    {
      "object_type": "FinancialIndicator",
      "join_field": "ts_code",
      "selected_columns": ["pe", "roe"]
    }
  ],
  "filters": [
    {"field": "FinancialIndicator.pe", "operator": "<", "value": 20}
  ]
}
```

## Common Query Patterns

### Pattern 1: Find Stocks by Criteria

```
User: "查找所有银行股"

1. list_objects (if not already done)
2. get_schema for "Stock"
3. query_data:
   - object_type: "Stock"
   - filters: [{"field": "industry", "operator": "=", "value": "银行"}]
```

### Pattern 2: Get Financial Metrics

```
User: "平安银行的市盈率和ROE"

1. query_data:
   - object_type: "Stock"
   - joins: [{"object_type": "FinancialIndicator", ...}]
   - filters: [{"field": "name", "operator": "like", "value": "%平安银行%"}]
   - selected_columns: ["Stock.name", "FinancialIndicator.pe", "FinancialIndicator.roe"]
```

### Pattern 3: Compare Multiple Stocks

```
User: "对比工商银行和建设银行的财务指标"

1. query_data with filters:
   - filters: [{"field": "name", "operator": "in", "value": ["工商银行", "建设银行"]}]
   - joins: [{"object_type": "FinancialIndicator", ...}]
```

## Semantic Types

The system automatically formats data based on semantic types:

- **currency** - Formatted with currency symbol (¥1,234.56)
- **percentage** - Shown as % (12.34%)
- **date** - Formatted dates (2024-03-26)
- **ratio** - Decimal ratios (1.23)
- **number** - Plain numbers with thousand separators

You don't need to format these manually - the system handles it.

## Best Practices

1. **Always explore first** - Use `list_objects` and `get_schema` before querying
2. **Use semantic types** - Let the system format currency, percentages, etc.
3. **Leverage default filters** - Objects may have auto-applied filters (like "only listed stocks")
4. **Save useful queries** - Use `save_asset` for queries you'll reuse
5. **Check relationships** - Use `get_relationships` to find valid joins
6. **Limit results** - Always use reasonable limits (default: 100)

## Error Handling

Common errors and solutions:

**"Invalid object_type"**
- Run `list_objects` to see available objects
- Check spelling and case sensitivity

**"Unknown field"**
- Run `get_schema` to see available fields
- For joined objects, use prefix: `ObjectName.field_name`

**"No data returned"**
- Check if default filters are too restrictive
- Verify filter values match data format
- Try broader filter criteria

**"Invalid relationship"**
- Run `get_relationships` to see valid joins
- Ensure join_field exists in both objects

## Examples

See the examples file for complete query scenarios.
