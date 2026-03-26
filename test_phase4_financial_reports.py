"""
Phase 4.1 测试 - 完整财务报表

测试新增的资产负债表和现金流量表对象
"""

import sys
sys.path.insert(0, 'backend')

from backend.tests.test_utils import setup_test_environment, print_section, load_config

# Setup test environment BEFORE importing app modules
setup_test_environment()

from app.services.omaha import OmahaService
import re


def test_balance_sheet():
    """测试资产负债表查询"""
    print_section("场景 1: 资产负债表查询 - 平安银行 (000001.SZ)")

    service = OmahaService()
    config_yaml = load_config()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="BalanceSheet",
        filters=[
            {"field": "ts_code", "operator": "=", "value": "000001.SZ"}
        ],
        limit=3
    )

    if result["success"]:
        print(f"✅ 查询成功，返回 {result['count']} 条记录\n")

        for i, record in enumerate(result["data"], 1):
            print(f"📊 记录 {i}:")
            print(f"  股票代码: {record.get('ts_code')}")
            print(f"  报告期: {record.get('end_date')}")
            print(f"  总资产: {record.get('total_assets')}")
            print(f"  总负债: {record.get('total_liab')}")
            print(f"  股东权益: {record.get('total_equity')}")
            print(f"  货币资金: {record.get('money_cap')}")
            print(f"  💡 资产负债率 (计算): {record.get('debt_to_asset_ratio')}")
            print(f"  💡 流动比率 (计算): {record.get('current_ratio')}")
            print(f"  💡 股东权益比率 (计算): {record.get('equity_ratio')}")
            print()
    else:
        print(f"❌ 查询失败: {result.get('error')}")


def test_cash_flow():
    """测试现金流量表查询"""
    print_section("场景 2: 现金流量表查询 - 平安银行 (000001.SZ)")

    service = OmahaService()
    config_yaml = load_config()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="CashFlow",
        filters=[
            {"field": "ts_code", "operator": "=", "value": "000001.SZ"}
        ],
        limit=3
    )

    if result["success"]:
        print(f"✅ 查询成功，返回 {result['count']} 条记录\n")

        for i, record in enumerate(result["data"], 1):
            print(f"📊 记录 {i}:")
            print(f"  股票代码: {record.get('ts_code')}")
            print(f"  报告期: {record.get('end_date')}")
            print(f"  经营活动现金流: {record.get('n_cashflow_act')}")
            print(f"  投资活动现金流: {record.get('n_cashflow_inv_act')}")
            print(f"  筹资活动现金流: {record.get('n_cash_flows_fnc_act')}")
            print(f"  期末现金余额: {record.get('c_cash_equ_end_period')}")
            print(f"  💡 现金净增加额 (计算): {record.get('cash_change')}")
            print(f"  💡 三大活动现金流合计 (计算): {record.get('total_cashflow')}")
            print()
    else:
        print(f"❌ 查询失败: {result.get('error')}")


def test_complete_financial_analysis():
    """测试完整财务分析 - 三张报表联合分析"""
    print_section("场景 3: 完整财务分析 - 平安银行最新财报")

    service = OmahaService()
    ts_code = "000001.SZ"
    config_yaml = load_config()

    # 查询利润表
    income = service.query_objects(
        config_yaml=config_yaml,
        object_type="IncomeStatement",
        filters=[{"field": "ts_code", "operator": "=", "value": ts_code}],
        limit=1
    )

    # 查询资产负债表
    balance = service.query_objects(
        config_yaml=config_yaml,
        object_type="BalanceSheet",
        filters=[{"field": "ts_code", "operator": "=", "value": ts_code}],
        limit=1
    )

    # 查询现金流量表
    cashflow = service.query_objects(
        config_yaml=config_yaml,
        object_type="CashFlow",
        filters=[{"field": "ts_code", "operator": "=", "value": ts_code}],
        limit=1
    )

    if income["success"] and balance["success"] and cashflow["success"]:
        print("✅ 三张报表查询成功\n")

        print("📈 利润表关键指标:")
        inc_data = income["data"][0]
        print(f"  营业总收入: {inc_data.get('total_revenue')}")
        print(f"  净利润: {inc_data.get('n_income')}")
        print(f"  净利率: {inc_data.get('profit_margin')}")

        print("\n📊 资产负债表关键指标:")
        bal_data = balance["data"][0]
        print(f"  总资产: {bal_data.get('total_assets')}")
        print(f"  总负债: {bal_data.get('total_liab')}")
        print(f"  资产负债率: {bal_data.get('debt_to_asset_ratio')}")

        print("\n💰 现金流量表关键指标:")
        cf_data = cashflow["data"][0]
        print(f"  经营现金流: {cf_data.get('n_cashflow_act')}")
        print(f"  投资现金流: {cf_data.get('n_cashflow_inv_act')}")
        print(f"  筹资现金流: {cf_data.get('n_cash_flows_fnc_act')}")

        print("\n💡 综合分析:")
        # 简单的财务健康度判断
        try:
            # 去除格式化符号进行计算
            net_income_str = str(inc_data.get('n_income', '0'))
            operating_cf_str = str(cf_data.get('n_cashflow_act', '0'))

            # 提取数字（去除 ¥、亿、万等符号）
            import re
            net_income_match = re.search(r'[\d.]+', net_income_str.replace('¥', '').replace('亿', '').replace('万', ''))
            operating_cf_match = re.search(r'[\d.]+', operating_cf_str.replace('¥', '').replace('亿', '').replace('万', ''))

            if net_income_match and operating_cf_match:
                net_income = float(net_income_match.group())
                operating_cf = float(operating_cf_match.group())

                if operating_cf > net_income:
                    print("  ✅ 经营现金流 > 净利润：利润质量高，真金白银")
                else:
                    print("  ⚠️  经营现金流 < 净利润：需关注应收账款和利润质量")
        except:
            print("  ℹ️  无法进行现金流质量分析")
    else:
        print("❌ 部分报表查询失败")


if __name__ == "__main__":
    print("🚀 Phase 4.1 财务报表测试开始...\n")

    test_balance_sheet()
    test_cash_flow()
    test_complete_financial_analysis()

    print_section("✅ 所有测试场景完成")
