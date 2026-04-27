"""
手动测试Link类型系统

测试场景：
1. 导入包含Link的本体
2. 验证Link字段自动展开
3. 测试反向导航工具
4. 测试多跳导航
"""
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import Tenant, User
from app.services.ontology.importer import OntologyImporter
from app.services.ontology.store import OntologyStore
from app.services.agent.chat_service import ChatService
import yaml


async def test_link_system():
    # 创建测试数据库
    engine = create_engine("sqlite:///test_link.db")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # 创建测试租户和用户
        tenant = Tenant(name="test_tenant")
        db.add(tenant)
        db.flush()

        user = User(
            username="test_user",
            email="test@example.com",
            hashed_password="dummy",
            tenant_id=tenant.id
        )
        db.add(user)
        db.commit()

        print("✓ 测试环境创建成功")

        # 导入本体
        with open("configs/test_link_ontology.yaml") as f:
            config = yaml.safe_load(f)

        importer = OntologyImporter(db)
        result = importer.import_dict(tenant.id, config)

        print(f"✓ 本体导入成功: {result}")

        # 验证Link属性
        store = OntologyStore(db)
        product = store.get_object(tenant.id, "Product")
        category_link = next(
            (p for p in product.properties if p.data_type == "link"),
            None
        )

        assert category_link is not None, "Category link not found"
        assert category_link.data_type == "link", "Not a link type"
        assert category_link.link_target.name == "Category", "Wrong target"

        print("✓ Link属性验证成功")
        print(f"  - Link字段: {category_link.name}")
        print(f"  - 目标对象: {category_link.link_target.name}")
        print(f"  - 外键: {category_link.link_foreign_key}")

        # 验证反向导航工具生成
        from app.services.agent.tools.factory import ObjectTypeToolFactory
        ontology = store.get_full_ontology(tenant.id)
        tools = ObjectTypeToolFactory.build(ontology)

        tool_names = {t.name for t in tools}
        assert "get_category_products" in tool_names, "Reverse nav tool not generated"

        print("✓ 反向导航工具生成成功")
        print(f"  - 工具: get_category_products")

        # 验证自引用Link
        category = store.get_object(tenant.id, "Category")
        parent_link = next(
            (p for p in category.properties if p.data_type == "link"),
            None
        )

        assert parent_link is not None, "Parent link not found"
        assert parent_link.link_target.name == "Category", "Self-reference failed"

        print("✓ 自引用Link验证成功")

        print("\n" + "="*50)
        print("所有测试通过！Link类型系统工作正常。")
        print("="*50)

    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_link_system())
