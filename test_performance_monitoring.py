#!/usr/bin/env python3
"""
性能监控测试 - 验证查询性能指标收集
"""

import requests
import json
import statistics

API_BASE = "http://69.5.23.70/api/public/v1"
API_TOKEN = "omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

def test_query_performance():
    """测试查询性能监控"""
    print("\n" + "="*80)
    print("查询性能监控测试")
    print("="*80)

    test_cases = [
        {
            "name": "简单查询 - Stock",
            "payload": {
                "object_type": "Stock",
                "filters": {"industry": "银行"},
                "limit": 10
            }
        },
        {
            "name": "复杂查询 - FinancialIndicator with computed",
            "payload": {
                "object_type": "FinancialIndicator",
                "filters": {"ts_code": "000001.SZ"},
                "limit": 100,
                "format": True,
                "select": ["end_date", "roe", "roa", "dupont_roe", "financial_health_score"]
            }
        },
        {
            "name": "聚合查询 - ValuationMetric",
            "payload": {
                "object_type": "ValuationMetric",
                "filters": {"ts_code": "000001.SZ"},
                "limit": 1000
            }
        }
    ]

    results = []

    for test in test_cases:
        print(f"\n测试: {test['name']}")
        times = []

        # 运行5次取平均值
        for i in range(5):
            resp = requests.post(f"{API_BASE}/query", headers=HEADERS, json=test['payload'])
            if resp.status_code == 200:
                data = resp.json()
                if 'execution_time_ms' in data:
                    times.append(data['execution_time_ms'])

        if times:
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)

            print(f"  平均响应时间: {avg_time:.2f}ms")
            print(f"  最快: {min_time}ms, 最慢: {max_time}ms")
            print(f"  记录数: {data.get('count', 0)}")

            results.append({
                "test": test['name'],
                "avg_ms": avg_time,
                "min_ms": min_time,
                "max_ms": max_time,
                "count": data.get('count', 0)
            })
        else:
            print(f"  ✗ 未获取到性能指标")

    # 总结
    print("\n" + "="*80)
    print("性能总结")
    print("="*80)

    for r in results:
        print(f"{r['test']}")
        print(f"  平均: {r['avg_ms']:.2f}ms | 记录数: {r['count']}")

    return len(results) == len(test_cases)

if __name__ == "__main__":
    success = test_query_performance()
    print("\n" + "="*80)
    if success:
        print("✓ 性能监控功能正常")
    else:
        print("✗ 性能监控功能异常")
    print("="*80)
