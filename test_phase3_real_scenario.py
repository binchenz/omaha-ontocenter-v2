"""
Phase 3 实际场景测试

测试语义类型格式化和计算属性在真实数据上的表现
"""

import sys
import os

# 设置环境变量（避免加载配置时报错）
os.environ.setdefault('DATABASE_URL', 'sqlite:///./omaha.db')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATAHUB_GMS_URL', 'http://localhost:8080')

sys.path.insert(0, 'backend')

from app.services.omaha import OmahaService
import json


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_financial_indicator():
    """测试场景 1: 财务指标查询（带格式化）"""
    print_section("场景 1: 财务指标查询 - 平安银行 (000001.SZ)")

    service = OmahaService()

    # 加载配置
    with open('configs/financial_stock_analysis.yaml', 'r', encoding='utf-8') as f:
        config_yaml = f.read()

    # 查询财务指标
    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="FinancialIndicator",
        filters=[
            {"field": "ts_code", "value": "000001.SZ"}
        ],
        selected_columns=[
            "ts_code", "end_date", "eps", "roe", "roa",
            "grossprofit_margin", "debt_to_assets",
            "ebit", "fcff", "financial_health_score"
        ],
        limit=3
    )

    if result["success"]:
        print(f"✅ 查询成功，返回 {result['count']} 条记录\n")

        for i, record in enumerate(result["data"], 1):
            print(f"📊 记录 {i}:")
            print(f"  股票代码: {record.get('ts_code', 'N/A')}")
            print(f"  报告期: {record.get('end_date', 'N/A')}")
            print(f"  每股收益: {record.get('eps', 'N/A')}")
            print(f"  净资产收益率 (ROE): {record.get('roe', 'N/A')}")
            print(f"  总资产报酬率 (ROA): {record.get('roa', 'N/A')}")
            print(f"  销售毛利率: {record.get('grossprofit_margin', 'N/A')}")
            print(f"  资产负债率: {record.get('debt_to_assets', 'N/A')}")
            print(f"  息税前利润 (EBIT): {record.get('ebit', 'N/A')}")
            print(f"  企业自由现金流 (FCFF): {record.get('fcff', 'N/A')}")
            print(f"  💡 财务健康度评分: {record.get('financial_health_score', 'N/A')}")
            print()
    else:
        print(f"❌ 查询失败: {result.get('error', 'Unknown error')}")


def test_income_statement():
    """测试场景 2: 利润表查询（带计算属性）"""
    print_section("场景 2: 利润表查询 - 平安银行 (000001.SZ)")

    service = OmahaService()

    # 加载配置
    with open('configs/financial_stock_analysis.yaml', 'r', encoding='utf-8') as f:
        config_yaml = f.read()

    # 查询利润表
    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="IncomeStatement",
        filters=[
            {"field": "ts_code", "value": "000001.SZ"}
        ],
        selected_columns=[
            "ts_code", "end_date", "total_revenue", "revenue",
            "operate_profit", "n_income", "n_income_attr_p",
            "profit_margin", "operating_margin"
        ],
        limit=3
    )

    if result["success"]:
        print(f"✅ 查询成功，返回 {result['count']} 条记录\n")

        for i, record in enumerate(result["data"], 1):
            print(f"📊 记录 {i}:")
            print(f"  股票代码: {record.get('ts_code', 'N/A')}")
            print(f"  报告期: {record.get('end_date', 'N/A')}")
            print(f"  营业总收入: {record.get('total_revenue', 'N/A')}")
            print(f"  营业收入: {record.get('revenue', 'N/A')}")
            print(f"  营业利润: {record.get('operate_profit', 'N/A')}")
            print(f"  净利润: {record.get('n_income', 'N/A')}")
            print(f"  归母净利润: {record.get('n_income_attr_p', 'N/A')}")
            print(f"  💡 净利率 (计算): {record.get('profit_margin', 'N/A')}")
            print(f"  💡 营业利润率 (计算): {record.get('operating_margin', 'N/A')}")
            print()
    else:
        print(f"❌ 查询失败: {result.get('error', 'Unknown error')}")


def test_multiple_stocks():
    """测试场景 3: 多股票对比"""
    print_section("场景 3: 多股票财务对比")

    service = OmahaService()

    # 加载配置
    with open('configs/financial_stock_analysis.yaml', 'r', encoding='utf-8') as f:
        config_yaml = f.read()

    stocks = [
        ("000001.SZ", "平安银行"),
        ("600000.SH", "浦发银行"),
        ("601398.SH", "工商银行")
    ]

    print("对比三家银行的最新财务指标：\n")

    for ts_code, name in stocks:
        result = service.query_objects(
            config_yaml=config_yaml,
            object_type="FinancialIndicator",
            filters=[
                {"field": "ts_code", "value": ts_code}
            ],
            selected_columns=[
                "ts_code", "end_date", "roe", "roa",
                "financial_health_score"
            ],
            limit=1
        )

        if result["success"] and result["count"] > 0:
            record = result["data"][0]
            print(f"🏦 {name} ({ts_code})")
            print(f"   报告期: {record.get('end_date', 'N/A')}")
            print(f"   ROE: {record.get('roe', 'N/A')}")
            print(f"   ROA: {record.get('roa', 'N/A')}")
            print(f"   财务健康度: {record.get('financial_health_score', 'N/A')}")
            print()


if __name__ == "__main__":
    print("\n🚀 Phase 3 实际场景测试开始...\n")

    try:
        # 场景 1: 财务指标
        test_financial_indicator()

        # 场景 2: 利润表
        test_income_statement()

        # 场景 3: 多股票对比
        test_multiple_stocks()

        print_section("✅ 所有测试场景完成")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
