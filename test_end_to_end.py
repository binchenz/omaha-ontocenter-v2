#!/usr/bin/env python3
"""
端到端验证测试 - 验证所有Ontology功能
确保系统完全正常工作
"""

import requests
import json
import sys

API_BASE = "http://69.5.23.70/api/public/v1"
API_TOKEN = "omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def test_api_health():
    """测试API健康状态"""
    print("\n" + "="*80)
    print("1. API健康检查")
    print("="*80)

    try:
        resp = requests.get("http://69.5.23.70/health", timeout=5)
        if resp.status_code == 200:
            print("✓ API运行正常")
            return True
        else:
            print(f"✗ API状态异常: {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接到API: {e}")
        return False


def test_list_objects():
    """测试列出所有对象"""
    print("\n" + "="*80)
    print("2. 列出所有对象类型")
    print("="*80)

    try:
        resp = requests.get(f"{API_BASE}/objects", headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            objects = data.get("objects", [])
            print(f"✓ 成功获取 {len(objects)} 个对象类型")
            for obj in objects:
                print(f"  - {obj['object_type']}: {obj['description'][:50]}...")
            return len(objects) == 11
        else:
            print(f"✗ 失败: {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_computed_properties():
    """测试计算属性"""
    print("\n" + "="*80)
    print("3. 测试计算属性")
    print("="*80)

    tests = [
        ("FinancialIndicator", ["dupont_roe", "financial_health_score"]),
        ("ValuationMetric", ["market_cap_billion", "free_float_ratio"]),
        ("TechnicalIndicator", ["trend_score", "ma_gap"]),
        ("DailyQuote", ["price_volatility", "volume_amount_ratio"])
    ]

    passed = 0
    for object_type, props in tests:
        payload = {
            "object_type": object_type,
            "filters": {"ts_code": "000001.SZ"},
            "limit": 1,
            "format": True,
            "select": props
        }

        try:
            resp = requests.post(f"{API_BASE}/query", headers=HEADERS, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if data["data"] and all(prop in data["data"][0] for prop in props):
                    print(f"✓ {object_type}: {', '.join(props)}")
                    passed += 1
                else:
                    print(f"✗ {object_type}: 计算属性缺失")
            else:
                print(f"✗ {object_type}: HTTP {resp.status_code}")
        except Exception as e:
            print(f"✗ {object_type}: {e}")

    return passed == len(tests)


def test_semantic_formatting():
    """测试语义格式化"""
    print("\n" + "="*80)
    print("4. 测试语义格式化")
    print("="*80)

    payload = {
        "object_type": "FinancialIndicator",
        "filters": {"ts_code": "000001.SZ"},
        "limit": 1,
        "format": True,
        "select": ["roe", "netprofit_margin"]
    }

    try:
        resp = requests.post(f"{API_BASE}/query", headers=HEADERS, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if data["data"]:
                record = data["data"][0]
                roe = record.get("roe", "")
                npm = record.get("netprofit_margin", "")

                if "%" in str(roe) and "%" in str(npm):
                    print(f"✓ 百分比格式化正常: ROE={roe}, 净利率={npm}")
                    return True
                else:
                    print(f"✗ 格式化失败: ROE={roe}, 净利率={npm}")
                    return False
        print(f"✗ 查询失败: {resp.status_code}")
        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_aggregate_query():
    """测试聚合查询"""
    print("\n" + "="*80)
    print("5. 测试聚合查询")
    print("="*80)

    payload = {
        "object_type": "Stock",
        "filters": {"industry": "银行"},
        "aggregations": [{"field": "ts_code", "function": "count"}]
    }

    try:
        resp = requests.post(f"{API_BASE}/aggregate", headers=HEADERS, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            count = data.get("results", {}).get("ts_code_count", 0)
            print(f"✓ 聚合查询成功: 银行股数量={count}")
            return count > 0
        else:
            print(f"✗ 失败: {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_sorting():
    """测试排序功能"""
    print("\n" + "="*80)
    print("6. 测试排序功能")
    print("="*80)

    payload = {
        "object_type": "FinancialIndicator",
        "filters": {"ts_code": "000001.SZ"},
        "order_by": "roe",
        "order": "desc",
        "limit": 3,
        "format": True,
        "select": ["end_date", "roe"]
    }

    try:
        resp = requests.post(f"{API_BASE}/query", headers=HEADERS, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if len(data["data"]) >= 2:
                print(f"✓ 排序功能正常")
                for record in data["data"]:
                    print(f"  {record['end_date']}: ROE={record['roe']}")
                return True
        print(f"✗ 排序失败")
        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def test_field_selection():
    """测试字段选择"""
    print("\n" + "="*80)
    print("7. 测试字段选择")
    print("="*80)

    payload = {
        "object_type": "Stock",
        "filters": {"industry": "银行"},
        "limit": 1,
        "select": ["ts_code", "name"]
    }

    try:
        resp = requests.post(f"{API_BASE}/query", headers=HEADERS, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            if data["data"]:
                record = data["data"][0]
                if len(record) == 2 and "ts_code" in record and "name" in record:
                    print(f"✓ 字段选择正常: {record}")
                    return True
                else:
                    print(f"✗ 返回了额外字段: {list(record.keys())}")
                    return False
        print(f"✗ 查询失败")
        return False
    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def main():
    print("\n" + "="*80)
    print("Ontology系统端到端验证测试")
    print("="*80)

    tests = [
        ("API健康检查", test_api_health),
        ("列出对象类型", test_list_objects),
        ("计算属性", test_computed_properties),
        ("语义格式化", test_semantic_formatting),
        ("聚合查询", test_aggregate_query),
        ("排序功能", test_sorting),
        ("字段选择", test_field_selection)
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 测试异常: {e}")
            results.append((name, False))

    # 总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")

    print("\n" + "="*80)
    print(f"总计: {passed}/{total} 测试通过 ({passed*100//total}%)")
    print("="*80)

    if passed == total:
        print("\n🎉 所有测试通过！Ontology系统完全正常！")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查系统状态")
        return 1


if __name__ == "__main__":
    sys.exit(main())
