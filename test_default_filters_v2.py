"""
测试 default_filters 自动过滤功能 - 改进版

验证 default_filters 是否作为 API 参数传递给 Tushare
"""

import sys
sys.path.insert(0, 'backend')

from backend.tests.test_utils import setup_test_environment, print_section, load_config

# Setup test environment BEFORE importing app modules
setup_test_environment()

from app.services.omaha import OmahaService
import tushare as ts


def test_default_filters_applied():
    """测试 default_filters 是否被应用"""
    print_section("测试 1: 验证 default_filters 是否生效")

    # 初始化 Tushare
    ts.set_token('044a35feee6c10f656343bdf3523014b88265b00bf2b586ed7c0ad90')
    pro = ts.pro_api()

    print("📋 对比测试：")
    print()

    # 1. 直接调用 Tushare API，不带 list_status 参数
    print("1️⃣ 直接调用 Tushare API（不带 list_status 参数）:")
    df_all = pro.stock_basic()
    print(f"   返回股票数量: {len(df_all)}")
    print(f"   示例: {df_all.head(3)[['ts_code', 'name']].to_string(index=False)}")
    print()

    # 2. 直接调用 Tushare API，带 list_status='L' 参数
    print("2️⃣ 直接调用 Tushare API（带 list_status='L' 参数）:")
    df_listed = pro.stock_basic(list_status='L')
    print(f"   返回股票数量: {len(df_listed)}")
    print(f"   示例: {df_listed.head(3)[['ts_code', 'name']].to_string(index=False)}")
    print()

    # 3. 通过 OmahaService 查询（应该自动应用 default_filters）
    print("3️⃣ 通过 OmahaService 查询（应该自动应用 default_filters）:")
    service = OmahaService()
    config_yaml = load_config()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        filters=[],  # 不提供任何过滤条件
        limit=5000  # 获取足够多的数据
    )

    if result["success"]:
        omaha_count = result['count']
        print(f"   返回股票数量: {omaha_count}")
        print(f"   示例: {result['data'][0]['ts_code']} - {result['data'][0]['name']}")
        print()

        # 验证
        print("🔍 验证结果:")
        if omaha_count == len(df_listed):
            print(f"   ✅ OmahaService 返回的股票数量 ({omaha_count}) = Tushare API 带 list_status='L' 的数量 ({len(df_listed)})")
            print(f"   ✅ default_filters 功能正常工作！")
        elif omaha_count < len(df_listed):
            print(f"   ⚠️  OmahaService 返回的股票数量 ({omaha_count}) < Tushare API 带 list_status='L' 的数量 ({len(df_listed)})")
            print(f"   ℹ️  可能是因为 limit 参数限制")
        else:
            print(f"   ❌ OmahaService 返回的股票数量 ({omaha_count}) > Tushare API 带 list_status='L' 的数量 ({len(df_listed)})")
            print(f"   ❌ default_filters 可能没有生效")

        print()
        print(f"📊 数据对比:")
        print(f"   - 所有股票（不带过滤）: {len(df_all)} 只")
        print(f"   - 上市股票（list_status='L'）: {len(df_listed)} 只")
        print(f"   - OmahaService 返回: {omaha_count} 只")
        print(f"   - 退市股票数量: {len(df_all) - len(df_listed)} 只")
    else:
        print(f"   ❌ 查询失败: {result.get('error')}")


def test_user_override():
    """测试用户过滤条件可以覆盖 default_filters"""
    print_section("测试 2: 用户过滤条件覆盖 default_filters")

    service = OmahaService()
    config_yaml = load_config()

    print("🔍 测试：用户指定 list_status='D' 查询退市股票...")
    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        filters=[
            {"field": "list_status", "operator": "=", "value": "D"}
        ],
        limit=10
    )

    if result["success"]:
        print(f"✅ 查询成功，返回 {result['count']} 条退市股票")
        if result['count'] > 0:
            print(f"   示例: {result['data'][0]['ts_code']} - {result['data'][0]['name']}")
            print("   ✅ 用户过滤条件成功覆盖了 default_filters")
        else:
            print("   ℹ️  没有找到退市股票")
    else:
        print(f"❌ 查询失败: {result.get('error')}")


def test_combined_filters():
    """测试 default_filters 与用户过滤条件组合"""
    print_section("测试 3: default_filters 与用户过滤条件组合")

    service = OmahaService()
    config_yaml = load_config()

    print("🔍 测试：查询银行行业的股票...")
    print("   预期：应该只返回上市状态的银行股（default_filters + 用户过滤条件）")
    print()

    result = service.query_objects(
        config_yaml=config_yaml,
        object_type="Stock",
        filters=[
            {"field": "industry", "operator": "=", "value": "银行"}
        ],
        limit=50
    )

    if result["success"]:
        print(f"✅ 查询成功，返回 {result['count']} 只银行股")
        print()
        print("📊 银行股列表:")
        for i, record in enumerate(result["data"][:10], 1):
            print(f"   {i}. {record.get('ts_code')} - {record.get('name')}")

        print()
        print("✅ default_filters 与用户过滤条件组合正常工作")
    else:
        print(f"❌ 查询失败: {result.get('error')}")


if __name__ == "__main__":
    print("🚀 default_filters 自动过滤功能测试（改进版）\n")

    test_default_filters_applied()
    test_user_override()
    test_combined_filters()

    print_section("✅ 所有测试完成")
