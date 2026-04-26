"""
Chat scenario tests for Phase 1 financial data objects.

This script simulates various chat queries to test the financial data objects
through the OmahaService API.
"""
import sys
sys.path.insert(0, '/Users/wangfushuaiqi/omaha_ontocenter/backend')

import os
from app.services.legacy.financial.omaha import OmahaService


def load_config():
    """Load the financial stock analysis configuration."""
    config_path = '/Users/wangfushuaiqi/omaha_ontocenter/configs/financial_stock_analysis.yaml'
    with open(config_path, 'r', encoding='utf-8') as f:
        return f.read()


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_case_1_basic_stock_query():
    """测试用例 1.1：查询所有上市股票"""
    print_section("测试用例 1.1：查询所有上市股票")

    config_yaml = load_config()
    os.environ['TUSHARE_TOKEN'] = '044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90'

    service = OmahaService()
    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        selected_columns=["ts_code", "name", "industry"],
        filters=[],
        limit=10
    )

    print(f"✓ 查询成功: {result['success']}")
    print(f"✓ 返回记录数: {len(result['data'])}")
    print(f"\n前5条记录:")
    for i, stock in enumerate(result['data'][:5], 1):
        print(f"  {i}. {stock['ts_code']} - {stock['name']} ({stock['industry']})")

    return result['success'] and len(result['data']) == 10


def test_case_2_specific_stock():
    """测试用例 1.2：查询特定股票信息"""
    print_section("测试用例 1.2：查询平安银行（000001.SZ）")

    config_yaml = load_config()
    service = OmahaService()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        selected_columns=["ts_code", "name", "industry", "area", "market", "list_date"],
        filters=[{"field": "ts_code", "value": "000001.SZ"}],
        limit=1
    )

    print(f"✓ 查询成功: {result['success']}")
    if result['data']:
        stock = result['data'][0]
        print(f"\n股票信息:")
        print(f"  代码: {stock['ts_code']}")
        print(f"  名称: {stock['name']}")
        print(f"  行业: {stock['industry']}")
        print(f"  地区: {stock['area']}")
        print(f"  市场: {stock['market']}")
        print(f"  上市日期: {stock['list_date']}")

    return result['success'] and len(result['data']) == 1


def test_case_3_daily_quotes():
    """测试用例 1.3：查询股票日线行情"""
    print_section("测试用例 1.3：查询 000001.SZ 最近10天行情")

    config_yaml = load_config()
    service = OmahaService()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="DailyQuote",
        selected_columns=["trade_date", "close", "pct_chg", "vol"],
        filters=[{"field": "ts_code", "value": "000001.SZ"}],
        limit=10
    )

    print(f"✓ 查询成功: {result['success']}")
    print(f"✓ 返回记录数: {len(result['data'])}")
    print(f"\n最近5天行情:")
    for quote in result['data'][:5]:
        print(f"  {quote['trade_date']}: ¥{quote['close']} ({quote.get('pct_chg', 0):+.2f}%)")

    return result['success'] and len(result['data']) > 0


def test_case_4_industry_list():
    """测试用例 1.4：查询所有行业"""
    print_section("测试用例 1.4：查询所有行业分类")

    config_yaml = load_config()
    service = OmahaService()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Industry",
        selected_columns=["industry"],
        filters=[],
        limit=20
    )

    print(f"✓ 查询成功: {result['success']}")
    print(f"✓ 返回记录数: {len(result['data'])}")

    # 提取唯一行业
    industries = list(set([row['industry'] for row in result['data']]))
    print(f"\n前10个行业:")
    for i, industry in enumerate(industries[:10], 1):
        print(f"  {i}. {industry}")

    return result['success'] and len(result['data']) > 0


def test_case_5_filter_by_industry():
    """测试用例 2.1：按行业筛选股票"""
    print_section("测试用例 2.1：查询银行行业的所有股票")

    config_yaml = load_config()
    service = OmahaService()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        selected_columns=["ts_code", "name", "industry"],
        filters=[{"field": "industry", "value": "银行"}],
        limit=10
    )

    print(f"✓ 查询成功: {result['success']}")
    print(f"✓ 返回记录数: {len(result['data'])}")
    print(f"\n银行股列表:")
    for i, stock in enumerate(result['data'], 1):
        print(f"  {i}. {stock['ts_code']} - {stock['name']}")

    # 验证所有股票都是银行行业
    all_banking = all(stock['industry'] == '银行' for stock in result['data'])
    print(f"\n✓ 所有股票都属于银行行业: {all_banking}")

    return result['success'] and all_banking


def test_case_6_stock_with_quotes():
    """测试用例 3.1：股票及其历史行情"""
    print_section("测试用例 3.1：查询平安银行及其最近5天行情")

    config_yaml = load_config()
    service = OmahaService()

    # Step 1: 查询股票信息
    stock_result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        selected_columns=["ts_code", "name", "industry"],
        filters=[{"field": "ts_code", "value": "000001.SZ"}],
        limit=1
    )

    print(f"✓ 股票查询成功: {stock_result['success']}")
    if stock_result['data']:
        stock = stock_result['data'][0]
        print(f"  股票: {stock['name']} ({stock['ts_code']})")

        # Step 2: 查询行情数据
        quote_result = service.query_objects(
            config_yaml=config_yaml,
            object_type="DailyQuote",
            selected_columns=["trade_date", "close", "pct_chg"],
            filters=[{"field": "ts_code", "value": stock['ts_code']}],
            limit=5
        )

        print(f"✓ 行情查询成功: {quote_result['success']}")
        print(f"✓ 返回行情记录数: {len(quote_result['data'])}")
        print(f"\n最近5天行情:")
        for quote in quote_result['data']:
            print(f"  {quote['trade_date']}: ¥{quote['close']} ({quote.get('pct_chg', 0):+.2f}%)")

        return stock_result['success'] and quote_result['success']

    return False


def test_case_7_price_analysis():
    """测试用例 4.2：股票价格走势分析"""
    print_section("测试用例 4.2：分析 000001.SZ 价格走势")

    config_yaml = load_config()
    service = OmahaService()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="DailyQuote",
        selected_columns=["trade_date", "close", "high", "low"],
        filters=[{"field": "ts_code", "value": "000001.SZ"}],
        limit=30
    )

    print(f"✓ 查询成功: {result['success']}")
    print(f"✓ 返回记录数: {len(result['data'])}")

    if result['data']:
        closes = [float(quote['close']) for quote in result['data']]
        highs = [float(quote['high']) for quote in result['data']]
        lows = [float(quote['low']) for quote in result['data']]

        avg_price = sum(closes) / len(closes)
        max_price = max(highs)
        min_price = min(lows)

        print(f"\n价格统计（最近{len(result['data'])}天）:")
        print(f"  平均收盘价: ¥{avg_price:.2f}")
        print(f"  最高价: ¥{max_price:.2f}")
        print(f"  最低价: ¥{min_price:.2f}")
        print(f"  价格波动: ¥{max_price - min_price:.2f} ({(max_price - min_price) / min_price * 100:.2f}%)")

    return result['success'] and len(result['data']) > 0


def test_case_8_volume_analysis():
    """测试用例 4.4：成交量分析"""
    print_section("测试用例 4.4：查询 000001.SZ 成交量和成交额")

    config_yaml = load_config()
    service = OmahaService()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="DailyQuote",
        selected_columns=["trade_date", "vol", "amount", "close"],
        filters=[{"field": "ts_code", "value": "000001.SZ"}],
        limit=10
    )

    print(f"✓ 查询成功: {result['success']}")
    print(f"✓ 返回记录数: {len(result['data'])}")

    if result['data']:
        print(f"\n最近10天成交情况:")
        for quote in result['data'][:10]:
            vol = float(quote['vol']) if quote['vol'] else 0
            amount = float(quote['amount']) if quote['amount'] else 0
            print(f"  {quote['trade_date']}: 成交量 {vol/10000:.2f}万手, 成交额 {amount/100000:.2f}亿元")

    return result['success'] and len(result['data']) > 0


def main():
    """Run all test cases."""
    print("\n" + "="*80)
    print("  Phase 1 金融数据对象 Chat 测试")
    print("="*80)

    test_cases = [
        ("基础查询 - 查询上市股票", test_case_1_basic_stock_query),
        ("基础查询 - 查询特定股票", test_case_2_specific_stock),
        ("基础查询 - 查询日线行情", test_case_3_daily_quotes),
        ("基础查询 - 查询行业列表", test_case_4_industry_list),
        ("过滤筛选 - 按行业筛选", test_case_5_filter_by_industry),
        ("关系查询 - 股票及行情", test_case_6_stock_with_quotes),
        ("复杂分析 - 价格走势分析", test_case_7_price_analysis),
        ("复杂分析 - 成交量分析", test_case_8_volume_analysis),
    ]

    results = []
    for name, test_func in test_cases:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            results.append((name, False))

    # Print summary
    print_section("测试总结")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"总测试数: {total}")
    print(f"通过: {passed}")
    print(f"失败: {total - passed}")
    print(f"通过率: {passed/total*100:.1f}%\n")

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {name}")

    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
