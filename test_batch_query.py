#!/usr/bin/env python3
"""
批量查询API - 一次查询多个股票
展示ontology在投资组合分析中的价值
"""

import requests
import json
from typing import List, Dict

API_BASE = "http://69.5.23.70/api/public/v1"
API_TOKEN = "omaha_hNDLNwGCBtK7JMfZcjxdRl96YKW1IX5CazquZV_-AXM"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}


def batch_query_stocks(stock_codes: List[str], object_type: str, select: List[str] = None, format: bool = True):
    """批量查询多个股票"""
    results = {}

    for code in stock_codes:
        payload = {
            "object_type": object_type,
            "filters": {"ts_code": code},
            "limit": 1,
            "format": format
        }

        if select:
            payload["select"] = select

        try:
            resp = requests.post(f"{API_BASE}/query", headers=HEADERS, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if data["data"]:
                    results[code] = data["data"][0]
                else:
                    results[code] = None
            else:
                results[code] = {"error": resp.status_code}
        except Exception as e:
            results[code] = {"error": str(e)}

    return results


def compare_financial_health(stock_codes: List[str]):
    """对比多个股票的财务健康度"""
    print("\n" + "=" * 80)
    print("财务健康度对比分析")
    print("=" * 80)

    results = batch_query_stocks(
        stock_codes,
        "FinancialIndicator",
        select=["ts_code", "end_date", "roe", "netprofit_margin", "financial_health_score", "dupont_roe"],
        format=True
    )

    print(f"\n{'股票代码':<12} {'报告期':<12} {'ROE':<10} {'净利率':<10} {'健康评分':<12} {'杜邦ROE':<10}")
    print("-" * 80)

    for code, data in results.items():
        if data and "error" not in data:
            print(f"{code:<12} {data.get('end_date', 'N/A'):<12} {data.get('roe', 'N/A'):<10} "
                  f"{data.get('netprofit_margin', 'N/A'):<10} {data.get('financial_health_score', 'N/A'):<12} "
                  f"{data.get('dupont_roe', 'N/A'):<10}")
        else:
            print(f"{code:<12} {'无数据' if not data else '错误'}")


def compare_valuation(stock_codes: List[str]):
    """对比多个股票的估值指标"""
    print("\n" + "=" * 80)
    print("估值指标对比分析")
    print("=" * 80)

    results = batch_query_stocks(
        stock_codes,
        "ValuationMetric",
        select=["ts_code", "trade_date", "pe", "pb", "market_cap_billion", "free_float_ratio"],
        format=True
    )

    print(f"\n{'股票代码':<12} {'日期':<12} {'PE':<10} {'PB':<10} {'市值(亿)':<12} {'流通比例':<12}")
    print("-" * 80)

    for code, data in results.items():
        if data and "error" not in data:
            print(f"{code:<12} {data.get('trade_date', 'N/A'):<12} {data.get('pe', 'N/A'):<10} "
                  f"{data.get('pb', 'N/A'):<10} {data.get('market_cap_billion', 'N/A'):<12} "
                  f"{data.get('free_float_ratio', 'N/A'):<12}")
        else:
            print(f"{code:<12} {'无数据' if not data else '错误'}")


def compare_technical_indicators(stock_codes: List[str]):
    """对比多个股票的技术指标"""
    print("\n" + "=" * 80)
    print("技术指标对比分析")
    print("=" * 80)

    results = batch_query_stocks(
        stock_codes,
        "TechnicalIndicator",
        select=["ts_code", "trade_date", "ma5", "ma20", "trend_score", "ma_gap"],
        format=True
    )

    print(f"\n{'股票代码':<12} {'日期':<12} {'MA5':<10} {'MA20':<10} {'趋势评分':<12} {'均线偏离':<12}")
    print("-" * 80)

    for code, data in results.items():
        if data and "error" not in data:
            print(f"{code:<12} {data.get('trade_date', 'N/A'):<12} {data.get('ma5', 'N/A'):<10} "
                  f"{data.get('ma20', 'N/A'):<10} {data.get('trend_score', 'N/A'):<12} "
                  f"{data.get('ma_gap', 'N/A'):<12}")
        else:
            print(f"{code:<12} {'无数据' if not data else '错误'}")


def main():
    # 银行股组合
    bank_stocks = ["000001.SZ", "600036.SH", "601398.SH", "601288.SH", "600000.SH"]

    print("\n" + "=" * 80)
    print("批量查询演示 - 银行股投资组合分析")
    print("=" * 80)
    print(f"\n分析股票: {', '.join(bank_stocks)}")

    # 1. 财务健康度对比
    compare_financial_health(bank_stocks)

    # 2. 估值指标对比
    compare_valuation(bank_stocks)

    # 3. 技术指标对比
    compare_technical_indicators(bank_stocks)

    print("\n" + "=" * 80)
    print("Ontology价值体现:")
    print("  ✓ 批量查询多个股票")
    print("  ✓ 自动计算23个计算属性")
    print("  ✓ 语义格式化（百分比、货币）")
    print("  ✓ 跨对象类型对比分析")
    print("=" * 80)


if __name__ == "__main__":
    main()
