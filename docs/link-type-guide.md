# Link Type System Guide

## Overview

The Link type system enables navigation between related objects in the ontology. It supports both forward and reverse navigation with automatic tool generation.

## Defining Links

### Basic Link Definition

```yaml
objects:
  stock:
    fields:
      - name: ts_code
        type: string
        semantic_type: stock_code
      - name: industry
        type: link
        target: industry
        link_field: industry_code
```

### Reverse Links

```yaml
objects:
  industry:
    fields:
      - name: industry_code
        type: string
      - name: stocks
        type: link
        target: stock
        reverse_of: industry
```

## Generated Tools

### Forward Navigation

For `stock.industry` link, generates:
- Tool: `get_stock_industry`
- Parameters: `ts_code` (stock identifier)
- Returns: Industry object

### Reverse Navigation

For `industry.stocks` link, generates:
- Tool: `get_industry_stocks`
- Parameters: `industry_code` (industry identifier)
- Returns: List of stock objects

### Multi-hop Navigation

Use `navigate_path` for complex queries:
```python
navigate_path(
    start_object="stock",
    start_id="000001.SZ",
    path="industry.stocks"
)
```

## Implementation Details

### Core Components

1. **LinkResolver** (`app/services/ontology/link_resolver.py`)
   - Resolves link definitions
   - Validates link targets
   - Handles forward/reverse links

2. **LinkExpander** (`app/services/agent/link_expander.py`)
   - Generates link navigation tools
   - Creates tool schemas
   - Registers tools with toolkit

3. **PathNavigator** (`app/services/agent/path_navigator.py`)
   - Executes multi-hop navigation
   - Handles path parsing
   - Aggregates results

### Database Schema

Link metadata stored in `object_properties` table:
- `link_target`: Target object type
- `link_field`: Join field name
- `reverse_of`: Reverse link reference

## Testing

Run Link system tests:
```bash
cd backend
pytest tests/unit/ontology/test_link_resolver.py
pytest tests/unit/agent/test_link_expander.py
pytest tests/unit/agent/test_path_navigator.py
pytest tests/integration/test_link_navigation.py
```

## Best Practices

1. Always define both forward and reverse links for bidirectional navigation
2. Use semantic types for link fields to ensure type safety
3. Test multi-hop paths before deploying to production
4. Document link relationships in ontology comments
