#!/usr/bin/env python3
"""
测试所有对象的计算属性
验证ontology的完整功能
"""

import requests
import json
from typing import Dict, List

API_BASE = "http://69.5.23.70/api/public/v1"
API_TOKEN = "omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# 测试配置：每个对象使用其计算属性
TEST_CONFIGS = [
    {
        "name": "DailyQuote",
        "filters": {"ts_code": "000001.SZ"},
        "select": ["trade_date", "close", "high", "low", "pct_chg", "price_volatility", "volume_amount_ratio"],
        "limit": 3
    },
    {
        "name": "ValuationMetric",
        "filters": {"ts_code": "000001.SZ", "trade_date": "20260326"},
        "select": ["trade_date", "total_mv", "market_cap_billion", "free_float_ratio"],
        "limit": 3
    },
    {
        "name": "FinancialIndicator",
        "filters": {"ts_code": "000001.SZ"},
        "select": ["end_date", "roe", "netprofit_margin", "financial_health_score", "dupont_roe"],
        "limit": 3
    },
    {
        "name": "TechnicalIndicator",
        "filters": {"ts_code": "000001.SZ"},
        "select": ["trade_date", "ma5", "ma20", "trend_score", "ma_gap"],
        "limit": 3
    },
    {
        "name": "BalanceSheet",
        "filters": {"ts_code": "000001.SZ"},
        "select": ["end_date", "total_assets", "total_liab", "debt_to_asset_ratio", "equity_ratio"],
        "limit": 3
    },
    {
        "name": "CashFlow",
        "filters": {"ts_code": "000001.SZ"},
        "select": ["end_date", "n_cashflow_act", "n_cashflow_inv_act", "cash_change", "total_cashflow"],
        "limit": 3
    },
    {
        "name": "IncomeStatement",
        "filters": {"ts_code": "000001.SZ"},
        "select": ["end_date", "total_revenue", "n_income", "profit_margin", "operating_margin"],
        "limit": 3
    }
]


def query_object(config: Dict) -> Dict:
    """查询单个对象"""
    payload = {
        "object_type": config["name"],
        "filters": config["filters"],
        "select": config.get("select"),
        "limit": config.get("limit", 3),
        "format": True
    }

    resp = requests.post(f"{API_BASE}/query", headers=HEADERS, json=payload)
    return resp.json()


def run_tests():
    print("=" * 60)
    print("Ontology Computed Properties Test Suite")
    print("=" * 60)

    results = {}
    passed = 0
    failed = 0

    for config in TEST_CONFIGS:
        name = config["name"]
        print(f"\n{'─' * 40}")
        print(f"Testing: {name}")

        try:
            data = query_object(config)

            if "data" in data and len(data["data"]) > 0:
                record = data["data"][0]
                print(f"  Records: {data['count']}")

                # Check computed properties are present and non-null
                select_fields = config.get("select", [])
                computed_found = []
                computed_null = []

                for field in select_fields:
                    if field in record:
                        val = record[field]
                        if val is not None and val != "":
                            computed_found.append(f"{field}={val}")
                        else:
                            computed_null.append(field)

                if computed_null:
                    print(f"  ⚠ NULL values: {', '.join(computed_null)}")
                    results[name] = "partial"
                else:
                    print(f"  ✓ All values present")
                    results[name] = "pass"
                    passed += 1

                # Show sample data
                print(f"  Sample: {json.dumps(record, ensure_ascii=False)[:200]}")

            else:
                print(f"  ✗ No data returned")
                print(f"  Response: {data}")
                results[name] = "fail"
                failed += 1

        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[name] = "error"
            failed += 1

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, status in results.items():
        icon = "✓" if status == "pass" else "⚠" if status == "partial" else "✗"
        print(f"  {icon} {name}: {status}")

    print(f"\nTotal: {len(TEST_CONFIGS)} objects tested")
    print(f"Passed: {passed}, Failed: {failed}, Partial: {len(TEST_CONFIGS) - passed - failed}")


if __name__ == "__main__":
    run_tests()
