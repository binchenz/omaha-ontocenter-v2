#!/usr/bin/env python3
"""Test Tushare Pro datasource integration."""
import sys
import os

# Set required environment variables
os.environ['DATABASE_URL'] = 'sqlite:///./omaha.db'
os.environ['SECRET_KEY'] = 'test-secret-key'
os.environ['DATAHUB_GMS_URL'] = 'http://localhost:8080'

sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

from app.services.omaha import omaha_service

# Read test config
with open('/Users/wangfushuaiqi/omaha_ontocenter/test_tushare_config.yaml', 'r') as f:
    config_yaml = f.read()

print("=" * 60)
print("测试 Tushare Pro 数据源接入")
print("=" * 60)

# Test 1: Parse config
print("\n1. 解析配置文件...")
result = omaha_service.parse_config(config_yaml)
if result['valid']:
    print("✓ 配置文件解析成功")
else:
    print(f"✗ 配置文件解析失败: {result['errors']}")
    sys.exit(1)

# Test 2: Query stock basic info (limit 5)
print("\n2. 查询股票基本信息（前5条）...")
result = omaha_service.query_objects(
    config_yaml=config_yaml,
    object_type='Stock',
    selected_columns=['ts_code', 'symbol', 'name', 'area', 'industry'],
    filters=None,
    limit=5
)

if result['success']:
    print(f"✓ 查询成功，返回 {result['count']} 条数据")
    print("\n股票列表:")
    for i, stock in enumerate(result['data'], 1):
        print(f"  {i}. {stock.get('ts_code')} - {stock.get('name')} ({stock.get('industry')})")
else:
    print(f"✗ 查询失败: {result['error']}")
    sys.exit(1)

# Test 3: Query with filter (上海地区)
print("\n3. 查询上海地区股票（前3条）...")
result = omaha_service.query_objects(
    config_yaml=config_yaml,
    object_type='Stock',
    selected_columns=['ts_code', 'name', 'area', 'industry'],
    filters=[{'field': 'area', 'value': '上海'}],
    limit=3
)

if result['success']:
    print(f"✓ 查询成功，返回 {result['count']} 条数据")
    if result['data']:
        print("\n上海地区股票:")
        for i, stock in enumerate(result['data'], 1):
            print(f"  {i}. {stock.get('ts_code')} - {stock.get('name')} ({stock.get('industry')})")
else:
    print(f"✗ 查询失败: {result['error']}")

print("\n" + "=" * 60)
print("✓ Tushare Pro 数据源接入测试完成！")
print("=" * 60)
