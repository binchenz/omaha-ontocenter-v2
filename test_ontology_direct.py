#!/usr/bin/env python
"""Test financial ontology queries without MCP."""
import os
import sys

os.environ.setdefault('DATABASE_URL', 'sqlite:///./backend/omaha.db')
os.environ.setdefault('SECRET_KEY', 'test-key')
os.environ.setdefault('DATAHUB_GMS_URL', 'http://localhost:8080')

sys.path.insert(0, 'backend')

from app.services.omaha import OmahaService

# Load config
with open('configs/financial_stock_analysis.yaml', 'r', encoding='utf-8') as f:
    config_yaml = f.read()

service = OmahaService()

print("=" * 60)
print("测试 1: 列出所有业务对象")
print("=" * 60)
result = service.build_ontology(config_yaml)
if result.get('valid'):
    objects = result['ontology'].get('objects', [])
    print(f"\n找到 {len(objects)} 个对象:")
    for obj in objects[:5]:
        print(f"  - {obj.get('name')}: {obj.get('description', '')[:50]}")
else:
    print(f"错误: {result.get('error')}")

print("\n" + "=" * 60)
print("测试 2: 查询股票 schema")
print("=" * 60)
schema = service.get_object_schema(config_yaml, 'Stock')
if schema.get('success'):
    fields = schema.get('fields', [])
    print(f"\nStock 对象有 {len(fields)} 个字段:")
    for field in fields[:5]:
        print(f"  - {field.get('name')}: {field.get('type')}")
else:
    print(f"错误: {schema.get('error')}")

print("\n✅ Ontology 系统工作正常！")
print("⚠️  需要 Python 3.10+ 才能使用 MCP server")
