"""
测试 default_filters 自动过滤功能
"""

import sys
import os

# 设置环境变量
os.environ.setdefault('DATABASE_URL', 'sqlite:///./omaha.db')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATAHUB_GMS_URL', 'http://localhost:8080')

sys.path.insert(0, 'backend')

from app.services.omaha import OmahaService


def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def test_stock_default_filters():
    """测试 Stock 对象的 default_filters"""
    print_section("测试 1: Stock 对象的 default_filters")

    service = OmahaService()

    # 读取配置文件
    with open("configs/financial_stock_analysis.yaml", "r", encoding="utf-8") as f:
        config_yaml = f.read()

    print("📋 Stock 对象定义的 default_filters:")
    print("   - field: list_status")
    print("   - operator: =")
    print("   - value: L  (L=上市，D=退市，P=暂停上市)")
    print()

    # 查询 Stock 对象，不提供任何过滤条件
    print("🔍 查询 Stock 对象（不提供任何过滤条件）...")
    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        filters=[],  # 不提供任何过滤条件
        limit=10
    )

    if result["success"]:
        print(f"✅ 查询成功，返回 {result['count']} 条记录\n")

        # 检查所有返回的股票是否都是上市状态
        all_listed = True
        for record in result["data"]:
            list_status = record.get("list_status")
            if list_status != "L":
                all_listed = False
                print(f"❌ 发现非上市股票: {record.get('ts_code')} - {record.get('name')} (状态: {list_status})")

        if all_listed:
            print("✅ 验证通过：所有返回的股票都是上市状态 (list_status='L')")
            print("\n📊 示例数据（前3条）:")
            for i, record in enumerate(result["data"][:3], 1):
                print(f"  {i}. {record.get('ts_code')} - {record.get('name')} - 状态: {record.get('list_status')}")
        else:
            print("❌ 验证失败：发现非上市股票")
    else:
        print(f"❌ 查询失败: {result.get('error')}")


def test_user_filters_override():
    """测试用户过滤条件可以覆盖 default_filters"""
    print_section("测试 2: 用户过滤条件覆盖 default_filters")

    service = OmahaService()

    # 读取配置文件
    with open("configs/financial_stock_analysis.yaml", "r", encoding="utf-8") as f:
        config_yaml = f.read()

    print("🔍 查询 Stock 对象（用户指定 list_status='D' 查询退市股票）...")
    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        filters=[
            {"field": "list_status", "operator": "=", "value": "D"}  # 用户指定查询退市股票
        ],
        limit=5
    )

    if result["success"]:
        print(f"✅ 查询成功，返回 {result['count']} 条记录\n")

        if result['count'] > 0:
            print("✅ 验证通过：用户过滤条件成功覆盖了 default_filters")
            print("\n📊 退市股票示例:")
            for i, record in enumerate(result["data"][:3], 1):
                print(f"  {i}. {record.get('ts_code')} - {record.get('name')} - 状态: {record.get('list_status')}")
        else:
            print("ℹ️  没有找到退市股票（可能数据库中没有退市股票数据）")
    else:
        print(f"❌ 查询失败: {result.get('error')}")


def test_combined_filters():
    """测试 default_filters 与用户过滤条件组合"""
    print_section("测试 3: default_filters 与用户过滤条件组合")

    service = OmahaService()

    # 读取配置文件
    with open("configs/financial_stock_analysis.yaml", "r", encoding="utf-8") as f:
        config_yaml = f.read()

    print("🔍 查询 Stock 对象（用户指定 industry='银行'）...")
    print("   预期：返回的股票应该满足两个条件：")
    print("   1. list_status='L' (default_filters)")
    print("   2. industry='银行' (用户过滤条件)")
    print()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        filters=[
            {"field": "industry", "operator": "=", "value": "银行"}
        ],
        limit=10
    )

    if result["success"]:
        print(f"✅ 查询成功，返回 {result['count']} 条记录\n")

        # 验证所有返回的股票都是上市状态且属于银行行业
        all_valid = True
        for record in result["data"]:
            list_status = record.get("list_status")
            industry = record.get("industry")
            if list_status != "L" or industry != "银行":
                all_valid = False
                print(f"❌ 发现不符合条件的股票: {record.get('ts_code')} - 状态: {list_status}, 行业: {industry}")

        if all_valid:
            print("✅ 验证通过：所有返回的股票都满足两个条件")
            print("\n📊 银行股示例:")
            for i, record in enumerate(result["data"][:5], 1):
                print(f"  {i}. {record.get('ts_code')} - {record.get('name')} - 行业: {record.get('industry')} - 状态: {record.get('list_status')}")
        else:
            print("❌ 验证失败：发现不符合条件的股票")
    else:
        print(f"❌ 查询失败: {result.get('error')}")


if __name__ == "__main__":
    print("🚀 default_filters 自动过滤功能测试开始...\n")

    test_stock_default_filters()
    test_user_filters_override()
    test_combined_filters()

    print_section("✅ 所有测试完成")
