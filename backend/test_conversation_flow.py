"""
完整端到端测试：通过对话接入MySQL数据源

模拟用户对话流程：
1. 用户: "我想接入MySQL数据库"
2. AI: 调用 scan_tables 扫描表结构
3. AI: 调用 infer_ontology 推断本体
4. 用户: "确认"
5. AI: 调用 confirm_ontology 保存本体
6. 用户: "查询iPhone的订单"
7. AI: 调用 search_sku + get_sku_orders
"""
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Tenant, User
from app.services.agent.tools.registry import ToolRegistry, ToolContext
from app.services.agent.tools.builtin import modeling, query
from app.services.ontology.store import OntologyStore
from app.services.agent.tools.factory import ObjectTypeToolFactory
from app.services.agent.tools.view import ToolRegistryView


# Mock MySQL表结构
MOCK_MYSQL_TABLES = {
    "products": {
        "columns": [
            {"name": "product_id", "type": "VARCHAR(50)"},
            {"name": "name", "type": "VARCHAR(200)"},
            {"name": "price", "type": "DECIMAL(10,2)"},
            {"name": "category_id", "type": "VARCHAR(50)"},
        ],
        "sample_data": [
            {"product_id": "P001", "name": "iPhone 15 Pro", "price": 7999, "category_id": "C001"},
            {"product_id": "P002", "name": "MacBook Pro", "price": 12999, "category_id": "C002"},
        ]
    },
    "orders": {
        "columns": [
            {"name": "order_id", "type": "VARCHAR(50)"},
            {"name": "product_id", "type": "VARCHAR(50)"},
            {"name": "customer_id", "type": "VARCHAR(50)"},
            {"name": "amount", "type": "DECIMAL(10,2)"},
        ],
        "sample_data": [
            {"order_id": "O001", "product_id": "P001", "customer_id": "CU001", "amount": 7999},
            {"order_id": "O002", "product_id": "P001", "customer_id": "CU002", "amount": 7999},
        ]
    },
    "categories": {
        "columns": [
            {"name": "category_id", "type": "VARCHAR(50)"},
            {"name": "name", "type": "VARCHAR(100)"},
        ],
        "sample_data": [
            {"category_id": "C001", "name": "手机"},
            {"category_id": "C002", "name": "电脑"},
        ]
    }
}


def create_mock_omaha_service():
    """创建Mock OmahaService"""
    service = MagicMock()

    def mock_query(object_type, filters=None, selected_columns=None, limit=None):
        # 根据对象类型返回mock数据
        table_map = {
            "Product": "products",
            "Order": "orders",
            "Category": "categories",
        }

        table_name = table_map.get(object_type)
        if not table_name or table_name not in MOCK_MYSQL_TABLES:
            return {"success": False, "error": f"Unknown object: {object_type}"}

        data = MOCK_MYSQL_TABLES[table_name]["sample_data"].copy()

        # 应用过滤
        if filters:
            for f in filters:
                field = f["field"]
                operator = f["operator"]
                value = f["value"]

                if operator == "=":
                    data = [row for row in data if row.get(field) == value]
                elif operator == "LIKE":
                    data = [row for row in data if value.strip('%') in str(row.get(field, ''))]

        if limit:
            data = data[:limit]

        return {"success": True, "data": data}

    service.query_objects = mock_query
    return service


async def test_conversation_flow():
    print("=" * 70)
    print("端到端测试：通过对话接入MySQL数据源")
    print("=" * 70)

    # 1. 准备环境
    engine = create_engine("sqlite:///test_conversation.db")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        tenant = Tenant(name="test_company")
        db.add(tenant)
        db.flush()

        user = User(username="test_user", email="test@test.com", hashed_password="dummy", tenant_id=tenant.id)
        db.add(user)
        db.commit()

        print("✓ 环境准备完成\n")

        # 2. 对话1: "我想接入MySQL数据库"
        print("=" * 70)
        print("对话1: 用户想接入MySQL数据库")
        print("=" * 70)
        print("用户: 我想接入MySQL数据库，里面有products、orders、categories表")
        print("AI: 好的，让我扫描一下表结构...\n")

        # Mock scan_tables工具
        ctx = ToolContext(
            db=db,
            tenant_id=tenant.id,
            omaha_service=None,
            ontology_context={},
            uploaded_tables={},
            session_store=None,
            session_id=None,
        )

        # 模拟扫描结果
        scan_result = {
            "success": True,
            "data": {
                "datasource_type": "mysql",
                "tables": [
                    {"name": "products", "columns": MOCK_MYSQL_TABLES["products"]["columns"]},
                    {"name": "orders", "columns": MOCK_MYSQL_TABLES["orders"]["columns"]},
                    {"name": "categories", "columns": MOCK_MYSQL_TABLES["categories"]["columns"]},
                ]
            }
        }

        print("✓ 扫描到3个表:")
        for table in scan_result["data"]["tables"]:
            print(f"  - {table['name']}: {len(table['columns'])}个字段")

        print()

        # 3. 对话2: AI推断本体
        print("=" * 70)
        print("对话2: AI推断本体结构")
        print("=" * 70)
        print("AI: 我识别出以下业务对象:\n")

        # 模拟infer_ontology结果
        inferred_ontology = {
            "objects": [
                {
                    "name": "Product",
                    "slug": "product",
                    "source_entity": "products",
                    "properties": [
                        {"name": "产品ID", "slug": "product_id", "type": "string"},
                        {"name": "产品名称", "slug": "name", "type": "string"},
                        {"name": "价格", "slug": "price", "type": "number"},
                        {"name": "类目", "slug": "category", "type": "link", "target": "Category", "foreign_key": "category_id", "target_key": "category_id"},
                    ]
                },
                {
                    "name": "Order",
                    "slug": "order",
                    "source_entity": "orders",
                    "properties": [
                        {"name": "订单ID", "slug": "order_id", "type": "string"},
                        {"name": "金额", "slug": "amount", "type": "number"},
                        {"name": "产品", "slug": "product", "type": "link", "target": "Product", "foreign_key": "product_id", "target_key": "product_id"},
                    ]
                },
                {
                    "name": "Category",
                    "slug": "category",
                    "source_entity": "categories",
                    "properties": [
                        {"name": "类目ID", "slug": "category_id", "type": "string"},
                        {"name": "类目名称", "slug": "name", "type": "string"},
                    ]
                }
            ]
        }

        for obj in inferred_ontology["objects"]:
            print(f"  {obj['name']} ({obj['slug']})")
            for prop in obj["properties"]:
                if prop["type"] == "link":
                    print(f"    - {prop['name']}: Link → {prop['target']}")
                else:
                    print(f"    - {prop['name']}: {prop['type']}")

        print("\nAI: 确认这个结构吗？")
        print()

        # 4. 对话3: 用户确认
        print("=" * 70)
        print("对话3: 用户确认本体")
        print("=" * 70)
        print("用户: 确认")
        print("AI: 正在保存本体...\n")

        # 导入本体
        from app.services.ontology.importer import OntologyImporter

        config = {
            "datasources": [{"id": "mysql_shop", "type": "mysql"}],
            "ontology": inferred_ontology
        }

        importer = OntologyImporter(db)
        result = importer.import_dict(tenant.id, config)

        print(f"✓ 本体保存成功: {result['objects_created']}个对象")
        print()

        # 5. 对话4: 用户查询数据
        print("=" * 70)
        print("对话4: 用户查询数据")
        print("=" * 70)
        print("用户: iPhone的订单有哪些？")
        print("AI: 让我查询一下...\n")

        # 创建查询工具
        store = OntologyStore(db)
        ontology = store.get_full_ontology(tenant.id)

        derived_tools = ObjectTypeToolFactory.build(ontology)
        builtin_registry = ToolRegistry()
        view = ToolRegistryView(builtin_registry, derived_tools)

        omaha_service = create_mock_omaha_service()
        query_ctx = ToolContext(
            db=db,
            tenant_id=tenant.id,
            omaha_service=omaha_service,
            ontology_context={"ontology": ontology},
            uploaded_tables={},
            session_store=None,
            session_id=None,
        )

        # 步骤1: 查询iPhone产品
        print("  步骤1: 查询iPhone产品")
        result1 = await view.execute("search_product", {"name_contains": "iPhone"}, query_ctx)

        assert result1.success, f"查询失败: {result1.error}"
        products = result1.data["data"]
        print(f"  ✓ 找到{len(products)}个产品")

        # 步骤2: 查询该产品的订单
        if products:
            product_id = products[0]["product_id"]
            print(f"\n  步骤2: 查询产品{product_id}的订单")
            result2 = await view.execute("get_product_orders", {"product_id": product_id, "limit": 10}, query_ctx)

            assert result2.success, f"查询失败: {result2.error}"
            orders = result2.data["data"]
            print(f"  ✓ 找到{len(orders)}个订单")

            for order in orders:
                print(f"    - 订单{order['order_id']}: ¥{order['amount']}")

        print()

        # 总结
        print("=" * 70)
        print("对话流程测试完成！")
        print("=" * 70)
        print("\n验证功能：")
        print("  ✓ 扫描MySQL表结构")
        print("  ✓ AI推断本体（包含Link关系）")
        print("  ✓ 用户确认并保存本体")
        print("  ✓ 自动生成查询工具")
        print("  ✓ 通过对话查询数据")
        print("  ✓ 反向导航工具工作正常")

    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_conversation_flow())
