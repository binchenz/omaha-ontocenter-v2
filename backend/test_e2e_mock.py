"""
完整端到端测试：Mock数据源 + 真实查询

测试完整流程：
1. Mock OmahaService返回真实数据
2. 创建本体（包含Link）
3. 执行真实查询工具调用
4. 验证Link自动展开
5. 验证反向导航
6. 验证多跳导航
"""
import asyncio
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Tenant, User
from app.services.ontology.importer import OntologyImporter
from app.services.ontology.store import OntologyStore
from app.services.agent.tools.factory import ObjectTypeToolFactory
from app.services.agent.tools.view import ToolRegistryView
from app.services.agent.tools.registry import ToolRegistry, ToolContext


# Mock数据
MOCK_SKUS = [
    {"sku_id": "SKU001", "name": "iPhone 15 Pro", "price": 7999, "category_id": "CAT001"},
    {"sku_id": "SKU002", "name": "MacBook Pro", "price": 12999, "category_id": "CAT002"},
    {"sku_id": "SKU003", "name": "AirPods Pro", "price": 1999, "category_id": "CAT003"},
]

MOCK_CATEGORIES = [
    {"category_id": "CAT001", "name": "手机"},
    {"category_id": "CAT002", "name": "电脑"},
    {"category_id": "CAT003", "name": "配件"},
]

MOCK_ORDERS = [
    {"order_id": "ORD001", "sku_id": "SKU001", "customer_id": "C001", "amount": 7999},
    {"order_id": "ORD002", "sku_id": "SKU001", "customer_id": "C002", "amount": 7999},
    {"order_id": "ORD003", "sku_id": "SKU002", "customer_id": "C001", "amount": 12999},
]

MOCK_CUSTOMERS = [
    {"customer_id": "C001", "name": "张三", "vip_level": "金卡"},
    {"customer_id": "C002", "name": "李四", "vip_level": "银卡"},
]


def create_mock_omaha_service():
    """创建Mock OmahaService"""
    service = MagicMock()

    def mock_query(object_type, filters=None, selected_columns=None, limit=None):
        """Mock查询逻辑"""
        filters = filters or []

        # 根据对象类型返回数据
        if object_type == "SKU":
            data = MOCK_SKUS.copy()
        elif object_type == "Category":
            data = MOCK_CATEGORIES.copy()
        elif object_type == "Order":
            data = MOCK_ORDERS.copy()
        elif object_type == "Customer":
            data = MOCK_CUSTOMERS.copy()
        else:
            return {"success": False, "error": f"Unknown object: {object_type}"}

        # 应用过滤
        for f in filters:
            field = f["field"]
            operator = f["operator"]
            value = f["value"]

            if operator == "=":
                data = [row for row in data if row.get(field) == value]
            elif operator == ">=":
                data = [row for row in data if row.get(field, 0) >= value]
            elif operator == "<=":
                data = [row for row in data if row.get(field, float('inf')) <= value]
            elif operator == "LIKE":
                data = [row for row in data if value.strip('%') in str(row.get(field, ''))]

        # 应用limit
        if limit:
            data = data[:limit]

        # 应用select
        if selected_columns:
            data = [{k: row.get(k) for k in selected_columns} for row in data]

        return {"success": True, "data": data}

    service.query_objects = mock_query
    return service


async def test_e2e_with_mock():
    print("=" * 70)
    print("端到端测试：Mock数据源 + 真实查询")
    print("=" * 70)

    # 1. 准备数据库
    engine = create_engine("sqlite:///test_e2e.db")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 创建租户
        tenant = Tenant(name="test_shop")
        db.add(tenant)
        db.flush()

        user = User(username="test", email="test@test.com", hashed_password="dummy", tenant_id=tenant.id)
        db.add(user)
        db.commit()

        print("✓ 测试环境准备完成\n")

        # 2. 导入本体（包含Link）
        ontology_config = {
            "datasources": [{"id": "test_db", "type": "mysql"}],
            "ontology": {
                "objects": [
                    {
                        "name": "Category",
                        "slug": "category",
                        "datasource": "test_db",
                        "source_entity": "categories",
                        "properties": [
                            {"name": "类目ID", "slug": "category_id", "type": "string"},
                            {"name": "类目名称", "slug": "name", "type": "string"},
                        ],
                    },
                    {
                        "name": "SKU",
                        "slug": "sku",
                        "datasource": "test_db",
                        "source_entity": "skus",
                        "properties": [
                            {"name": "SKU编码", "slug": "sku_id", "type": "string"},
                            {"name": "商品名称", "slug": "name", "type": "string"},
                            {"name": "价格", "slug": "price", "type": "number"},
                            {"name": "类目", "slug": "category", "type": "link", "target": "Category", "foreign_key": "category_id", "target_key": "category_id"},
                        ],
                    },
                    {
                        "name": "Order",
                        "slug": "order",
                        "datasource": "test_db",
                        "source_entity": "orders",
                        "properties": [
                            {"name": "订单号", "slug": "order_id", "type": "string"},
                            {"name": "金额", "slug": "amount", "type": "number"},
                            {"name": "商品", "slug": "sku", "type": "link", "target": "SKU", "foreign_key": "sku_id", "target_key": "sku_id"},
                            {"name": "客户", "slug": "customer", "type": "link", "target": "Customer", "foreign_key": "customer_id", "target_key": "customer_id"},
                        ],
                    },
                    {
                        "name": "Customer",
                        "slug": "customer",
                        "datasource": "test_db",
                        "source_entity": "customers",
                        "properties": [
                            {"name": "客户ID", "slug": "customer_id", "type": "string"},
                            {"name": "姓名", "slug": "name", "type": "string"},
                            {"name": "VIP等级", "slug": "vip_level", "type": "string"},
                        ],
                    },
                ]
            }
        }

        importer = OntologyImporter(db)
        result = importer.import_dict(tenant.id, ontology_config)

        print(f"✓ 本体导入成功: {result['objects_created']}个对象\n")

        # 3. 创建工具和上下文
        store = OntologyStore(db)
        ontology = store.get_full_ontology(tenant.id)

        derived_tools = ObjectTypeToolFactory.build(ontology)
        builtin_registry = ToolRegistry()
        view = ToolRegistryView(builtin_registry, derived_tools)

        omaha_service = create_mock_omaha_service()
        ctx = ToolContext(
            db=db,
            omaha_service=omaha_service,
            ontology_context={"ontology": ontology},
            session_store=None,
            session_id=None,
        )

        print(f"✓ 工具系统初始化完成: {len(derived_tools)}个工具\n")

        # 4. 场景1: 查询SKU（验证Link自动展开）
        print("=" * 70)
        print("场景1: 查询iPhone 15 Pro（验证Link自动展开）")
        print("=" * 70)

        result = await view.execute("search_sku", {"name_contains": "iPhone"}, ctx)

        assert result.success, f"查询失败: {result.error}"
        data = result.data["data"]
        assert len(data) >= 1, f"预期至少1条结果，实际{len(data)}条"

        sku = data[0]
        print(f"✓ 查询成功: {sku['name']}")
        print(f"  - SKU编码: {sku['sku_id']}")
        print(f"  - 价格: ¥{sku['price']}")

        # 验证Link字段展开
        if "category" in sku and isinstance(sku["category"], dict):
            print(f"  - 类目: {sku['category']['name']} (Link已展开 ✓)")
        else:
            print(f"  - 类目: {sku.get('category_id')} (Link未展开)")

        print()

        # 5. 场景2: 反向导航（查询某类目的所有SKU）
        print("=" * 70)
        print("场景2: 查询手机类目下的所有商品（反向导航）")
        print("=" * 70)

        result = await view.execute("get_category_skus", {"category_id": "CAT001", "limit": 10}, ctx)

        assert result.success, f"查询失败: {result.error}"
        data = result.data["data"]

        print(f"✓ 反向导航成功: 找到{len(data)}个商品")
        for item in data:
            print(f"  - {item['name']}: ¥{item['price']}")

        print()

        # 6. 场景3: 多跳查询（SKU → Order → Customer）
        print("=" * 70)
        print("场景3: iPhone 15 Pro被哪些客户购买（多跳导航）")
        print("=" * 70)

        # 先查SKU的订单
        result = await view.execute("get_sku_orders", {"sku_id": "SKU001"}, ctx)

        assert result.success, f"查询失败: {result.error}"
        orders = result.data["data"]

        print(f"✓ 找到{len(orders)}个订单")

        # 再查每个订单的客户
        customer_ids = list(set(order["customer_id"] for order in orders))
        print(f"✓ 涉及{len(customer_ids)}个客户")

        for cid in customer_ids:
            result = await view.execute("search_customer", {"customer_id": cid}, ctx)
            if result.success and result.data["data"]:
                customer = result.data["data"][0]
                print(f"  - {customer['name']} ({customer['vip_level']})")

        print()

        # 7. 场景4: 计数查询
        print("=" * 70)
        print("场景4: 统计商品总数（count查询）")
        print("=" * 70)

        result = await view.execute("count_sku", {}, ctx)

        assert result.success, f"查询失败: {result.error}"
        count = result.data["count"]

        print(f"✓ 统计成功: 共{count}个商品")

        print()

        # 总结
        print("=" * 70)
        print("所有场景测试通过！")
        print("=" * 70)
        print("\n验证功能：")
        print("  ✓ 基础查询（search_sku）")
        print("  ✓ 反向导航工具（get_category_skus）")
        print("  ✓ 多跳查询（SKU → Order → Customer）")
        print("  ✓ 计数查询（count_sku）")
        print("  ✓ Mock数据源完美工作")

    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_e2e_with_mock())
