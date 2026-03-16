#!/usr/bin/env python3
"""
Ontology 设计验证脚本
验证 ontology_redesign_v2.yaml 的设计是否与实际数据库匹配
"""

import pymysql
import yaml
from typing import Dict, List, Set

# 数据库连接配置
DB_CONFIG = {
    'host': '60.190.243.69',
    'port': 9030,
    'user': 'agent_write',
    'password': 'Batch@Sr2026!Agent',
    'database': 'agent',
    'charset': 'utf8mb4'
}

def load_ontology(yaml_path: str) -> Dict:
    """加载 Ontology YAML 文件"""
    with open(yaml_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_table_columns(conn, table_name: str) -> Set[str]:
    """获取表的所有列名"""
    cursor = conn.cursor()
    cursor.execute(f'DESCRIBE {table_name}')
    columns = {row[0] for row in cursor.fetchall()}
    cursor.close()
    return columns

def validate_object(conn, obj: Dict) -> List[str]:
    """验证单个对象的定义"""
    errors = []
    obj_name = obj.get('name', 'Unknown')

    # 跳过使用 query 定义的对象
    if 'query' in obj:
        print(f"  ✓ {obj_name}: 使用自定义查询，跳过列验证")
        return errors

    table_name = obj.get('table')
    if not table_name:
        errors.append(f"{obj_name}: 缺少 table 定义")
        return errors

    # 获取表的实际列
    try:
        actual_columns = get_table_columns(conn, table_name)
    except Exception as e:
        errors.append(f"{obj_name}: 无法获取表 {table_name} 的列信息 - {e}")
        return errors

    # 验证属性定义
    properties = obj.get('properties', [])
    for prop in properties:
        prop_name = prop.get('name')
        column_name = prop.get('column', prop_name)

        if column_name not in actual_columns:
            errors.append(f"{obj_name}.{prop_name}: 列 '{column_name}' 不存在于表 {table_name}")

    # 检查粒度定义
    if 'granularity' not in obj:
        errors.append(f"{obj_name}: 缺少 granularity 定义")
    else:
        granularity = obj['granularity']
        if 'dimensions' not in granularity:
            errors.append(f"{obj_name}: granularity 缺少 dimensions")
        if 'level' not in granularity:
            errors.append(f"{obj_name}: granularity 缺少 level")
        if 'description' not in granularity:
            errors.append(f"{obj_name}: granularity 缺少 description")

    if not errors:
        print(f"  ✓ {obj_name}: 验证通过")

    return errors

def main():
    print("=" * 60)
    print("Ontology 设计验证")
    print("=" * 60)

    # 加载 Ontology
    yaml_path = 'docs/superpowers/ontology_redesign_v2.yaml'
    print(f"\n加载 Ontology: {yaml_path}")
    ontology = load_ontology(yaml_path)

    # 连接数据库
    print("\n连接数据库...")
    conn = pymysql.connect(**DB_CONFIG)
    print("✓ 数据库连接成功")

    # 验证所有对象
    print("\n验证对象定义:")
    print("-" * 60)

    all_errors = []
    objects = ontology.get('ontology', {}).get('objects', [])

    for obj in objects:
        errors = validate_object(conn, obj)
        all_errors.extend(errors)

    # 输出结果
    print("\n" + "=" * 60)
    print("验证结果")
    print("=" * 60)

    if all_errors:
        print(f"\n❌ 发现 {len(all_errors)} 个问题:\n")
        for error in all_errors:
            print(f"  • {error}")
    else:
        print("\n✅ 所有验证通过！")

    # 统计信息
    print("\n" + "=" * 60)
    print("统计信息")
    print("=" * 60)
    print(f"对象数量: {len(objects)}")

    # 统计粒度级别
    granularity_levels = {}
    for obj in objects:
        if 'granularity' in obj:
            level = obj['granularity'].get('level', 'unknown')
            granularity_levels[level] = granularity_levels.get(level, 0) + 1

    print("\n粒度级别分布:")
    for level, count in sorted(granularity_levels.items()):
        print(f"  • {level}: {count} 个对象")

    # 关闭连接
    conn.close()

    return 0 if not all_errors else 1

if __name__ == '__main__':
    exit(main())
