#!/usr/bin/env python3
"""
测试新增语义类型 - ratio, growth_rate, score, multiplier
"""

import requests
import json

API_BASE = "http://69.5.23.70/api/public/v1"
API_TOKEN = "omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def test_semantic_types():
    """测试新增语义类型格式化"""
    print("\n" + "="*80)
    print("新增语义类型测试")
    print("="*80)

    # 测试数据
    test_cases = [
        {
            "type": "ratio",
            "value": 15.67,
            "expected": "15.67x",
            "description": "市盈率格式化"
        },
        {
            "type": "growth_rate",
            "value": 23.5,
            "expected": "+23.50%",
            "description": "正增长率"
        },
        {
            "type": "growth_rate",
            "value": -12.3,
            "expected": "-12.30%",
            "description": "负增长率"
        },
        {
            "type": "score",
            "value": 85.6,
            "expected": "85.6分",
            "description": "评分格式化"
        },
        {
            "type": "multiplier",
            "value": 3.45,
            "expected": "3.45倍",
            "description": "倍数格式化"
        }
    ]

    # 本地测试格式化函数
    from backend.app.services.semantic_formatter import SemanticTypeFormatter

    passed = 0
    failed = 0

    for test in test_cases:
        result = SemanticTypeFormatter.format_value(test["value"], test["type"])
        if result == test["expected"]:
            print(f"✓ {test['description']}: {test['value']} → {result}")
            passed += 1
        else:
            print(f"✗ {test['description']}: 期望 {test['expected']}, 实际 {result}")
            failed += 1

    print("\n" + "="*80)
    print(f"总计: {passed + failed} 个测试")
    print(f"通过: {passed}, 失败: {failed}")
    print("="*80)

    return failed == 0

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter')

    success = test_semantic_types()
    sys.exit(0 if success else 1)
