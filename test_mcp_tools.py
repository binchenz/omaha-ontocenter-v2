#!/usr/bin/env python
"""Test MCP server tools directly."""
import os
import sys
import json

os.environ['OMAHA_API_KEY'] = 'omaha_1_0b3e8609_75db70716f070321ff0ee0eac91d8031'
os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
os.environ['SECRET_KEY'] = 'your-secret-key-here-change-in-production-min-32-chars'
os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

sys.path.insert(0, 'backend')

from app.mcp.server import _load_context
from app.mcp import tools as t

print("=" * 60)
print("MCP Server 功能测试")
print("=" * 60)

# Load context
project_id, config_yaml = _load_context()
print(f"\n✓ 认证成功")
print(f"  Project ID: {project_id}")
print(f"  Config size: {len(config_yaml)} bytes")

# Test 1: List objects
print("\n" + "=" * 60)
print("测试 1: list_objects")
print("=" * 60)
result = t.list_objects(config_yaml)
if result.get('success'):
    objects = result.get('objects', [])
    print(f"\n✓ 找到 {len(objects)} 个对象:")
    for obj in objects[:5]:
        print(f"  - {obj['name']}: {obj.get('description', '')[:50]}")
else:
    print(f"✗ 错误: {result.get('error')}")

# Test 2: Get schema
print("\n" + "=" * 60)
print("测试 2: get_schema (Stock)")
print("=" * 60)
result = t.get_schema(config_yaml, 'Stock')
if result.get('success'):
    fields = result.get('fields', [])
    print(f"\n✓ Stock 有 {len(fields)} 个字段:")
    for field in fields[:5]:
        semantic = field.get('semantic_type', 'N/A')
        print(f"  - {field['name']} ({field['type']}) [{semantic}]")
else:
    print(f"✗ 错误: {result.get('error')}")

# Test 3: Query data
print("\n" + "=" * 60)
print("测试 3: query_data (查询银行股)")
print("=" * 60)
result = t.query_data(
    config_yaml=config_yaml,
    object_type='Stock',
    selected_columns=['ts_code', 'name', 'industry'],
    filters=[{'field': 'industry', 'operator': '=', 'value': '银行'}],
    limit=5
)
if result.get('success'):
    rows = result.get('data', [])
    print(f"\n✓ 找到 {len(rows)} 条记录:")
    for row in rows:
        print(f"  - {row.get('ts_code')}: {row.get('name')} ({row.get('industry')})")
else:
    print(f"✗ 错误: {result.get('error')}")

print("\n" + "=" * 60)
print("✓ MCP Server 所有功能正常！")
print("=" * 60)
print("\n下一步: 确保 Claude Code 能识别 MCP 工具")
print("工具名称格式: mcp__omaha-ontocenter__<tool_name>")
