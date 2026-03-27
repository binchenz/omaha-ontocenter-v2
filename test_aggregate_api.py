#!/usr/bin/env python3
"""
测试聚合查询API
展示ontology的统计分析能力
"""

import requests
import json

API_BASE = "http://69.5.23.70/api/public/v1"
API_TOKEN = "omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# 测试用例
TEST_CASES = [
    {
        "name": "统计所有股票数量",
        "request": {
            "object_type": "Stock",
            "filters": {},
            "aggregations": [{"field": "ts_code", "function": "count"}]
        }
    },
    {
        "name": "统计银行业股票数量",
        "request": {
            "object_type": "Stock",
            "filters": {"industry": "银行"},
            "aggregations": [{"field": "ts_code", "function": "count"}]
        }
    },
    {
        "name": "平安银行ROE统计（平均、最大、最小）",
        "request": {
            "object_type": "FinancialIndicator",
            "filters": {"ts_code": "000001.SZ"},
            "aggregations": [
                {"field": "roe", "function": "avg"},
                {"field": "roe", "function": "max"},
                {"field": "roe", "function": "min"}
            ]
        }
    },
    {
        "name": "平安银行市值统计",
        "request": {
            "object_type": "ValuationMetric",
            "filters": {"ts_code": "000001.SZ"},
            "aggregations": [
                {"field": "total_mv", "function": "avg"},
                {"field": "total_mv", "function": "max"}
            ]
        }
    },
    {
        "name": "平安银行日线价格统计",
        "request": {
            "object_type": "DailyQuote",
            "filters": {"ts_code": "000001.SZ"},
            "aggregations": [
                {"field": "close", "function": "avg"},
                {"field": "close", "function": "max"},
                {"field": "close", "function": "min"}
            ]
        }
    }
]


def run_aggregate_test(test_case):
    """运行单个聚合测试"""
    print(f"\n{'─' * 60}")
    print(f"测试: {test_case['name']}")
    print(f"请求: {json.dumps(test_case['request'], ensure_ascii=False)}")

    try:
        resp = requests.post(
            f"{API_BASE}/aggregate",
            headers=HEADERS,
            json=test_case['request']
        )

        if resp.status_code == 200:
            data = resp.json()
            print(f"✓ 成功")
            print(f"  记录数: {data['count']}")
            print(f"  结果: {json.dumps(data['results'], ensure_ascii=False, indent=2)}")
            return True
        else:
            print(f"✗ 失败: {resp.status_code}")
            print(f"  响应: {resp.text}")
            return False

    except Exception as e:
        print(f"✗ 错误: {e}")
        return False


def main():
    print("=" * 60)
    print("聚合查询API测试")
    print("=" * 60)

    passed = 0
    failed = 0

    for test_case in TEST_CASES:
        if run_aggregate_test(test_case):
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"总计: {len(TEST_CASES)} 个测试")
    print(f"通过: {passed}, 失败: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
