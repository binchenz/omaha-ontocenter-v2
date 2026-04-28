"""
创建测试数据：MySQL + Excel

场景：电商系统
- MySQL: 商品表(products)、订单表(orders)
- Excel: 客户VIP等级表(customers.xlsx)
"""
import pandas as pd
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"
    product_id = Column(String(50), primary_key=True)
    name = Column(String(200))
    price = Column(Float)
    stock = Column(Integer)
    category_id = Column(String(50))


class Order(Base):
    __tablename__ = "orders"
    order_id = Column(String(50), primary_key=True)
    product_id = Column(String(50))
    customer_id = Column(String(50))
    quantity = Column(Integer)
    amount = Column(Float)
    order_date = Column(DateTime)


class Category(Base):
    __tablename__ = "categories"
    category_id = Column(String(50), primary_key=True)
    name = Column(String(100))
    parent_id = Column(String(50), nullable=True)


def create_test_data():
    print("=" * 70)
    print("创建测试数据：MySQL + Excel")
    print("=" * 70)

    # 1. 创建MySQL数据库
    engine = create_engine("sqlite:///test_shop.db")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 插入类目数据
        categories = [
            Category(category_id="CAT001", name="手机", parent_id=None),
            Category(category_id="CAT002", name="电脑", parent_id=None),
            Category(category_id="CAT003", name="配件", parent_id=None),
            Category(category_id="CAT004", name="iPhone", parent_id="CAT001"),
            Category(category_id="CAT005", name="Android", parent_id="CAT001"),
        ]
        session.add_all(categories)

        # 插入商品数据
        products = [
            Product(product_id="P001", name="iPhone 15 Pro", price=7999, stock=50, category_id="CAT004"),
            Product(product_id="P002", name="iPhone 15", price=5999, stock=100, category_id="CAT004"),
            Product(product_id="P003", name="MacBook Pro 14", price=12999, stock=30, category_id="CAT002"),
            Product(product_id="P004", name="MacBook Air", price=7999, stock=60, category_id="CAT002"),
            Product(product_id="P005", name="AirPods Pro", price=1999, stock=200, category_id="CAT003"),
            Product(product_id="P006", name="Magic Mouse", price=799, stock=150, category_id="CAT003"),
            Product(product_id="P007", name="小米14 Pro", price=4999, stock=80, category_id="CAT005"),
            Product(product_id="P008", name="华为Mate 60", price=6999, stock=70, category_id="CAT005"),
        ]
        session.add_all(products)

        # 插入订单数据
        orders = [
            Order(order_id="O001", product_id="P001", customer_id="C001", quantity=1, amount=7999, order_date=datetime(2024, 4, 1)),
            Order(order_id="O002", product_id="P001", customer_id="C002", quantity=1, amount=7999, order_date=datetime(2024, 4, 2)),
            Order(order_id="O003", product_id="P002", customer_id="C001", quantity=2, amount=11998, order_date=datetime(2024, 4, 3)),
            Order(order_id="O004", product_id="P003", customer_id="C003", quantity=1, amount=12999, order_date=datetime(2024, 4, 4)),
            Order(order_id="O005", product_id="P005", customer_id="C002", quantity=3, amount=5997, order_date=datetime(2024, 4, 5)),
            Order(order_id="O006", product_id="P007", customer_id="C004", quantity=1, amount=4999, order_date=datetime(2024, 4, 6)),
            Order(order_id="O007", product_id="P001", customer_id="C005", quantity=1, amount=7999, order_date=datetime(2024, 4, 7)),
            Order(order_id="O008", product_id="P003", customer_id="C001", quantity=1, amount=12999, order_date=datetime(2024, 4, 8)),
            Order(order_id="O009", product_id="P005", customer_id="C003", quantity=2, amount=3998, order_date=datetime(2024, 4, 9)),
            Order(order_id="O010", product_id="P008", customer_id="C005", quantity=1, amount=6999, order_date=datetime(2024, 4, 10)),
        ]
        session.add_all(orders)

        session.commit()

        print("\n✓ MySQL数据创建成功 (test_shop.db)")
        print(f"  - 类目: {len(categories)}条")
        print(f"  - 商品: {len(products)}条")
        print(f"  - 订单: {len(orders)}条")

    finally:
        session.close()

    # 2. 创建Excel数据
    customers_data = [
        {"customer_id": "C001", "name": "张三", "vip_level": "金卡", "phone": "13800138001", "city": "北京"},
        {"customer_id": "C002", "name": "李四", "vip_level": "银卡", "phone": "13800138002", "city": "上海"},
        {"customer_id": "C003", "name": "王五", "vip_level": "金卡", "phone": "13800138003", "city": "深圳"},
        {"customer_id": "C004", "name": "赵六", "vip_level": "普通", "phone": "13800138004", "city": "广州"},
        {"customer_id": "C005", "name": "钱七", "vip_level": "银卡", "phone": "13800138005", "city": "杭州"},
    ]

    df = pd.DataFrame(customers_data)
    df.to_excel("test_customers.xlsx", index=False)

    print("\n✓ Excel数据创建成功 (test_customers.xlsx)")
    print(f"  - 客户: {len(customers_data)}条")

    # 3. 打印数据概览
    print("\n" + "=" * 70)
    print("数据概览")
    print("=" * 70)

    print("\n【类目层级】")
    print("  手机 (CAT001)")
    print("    ├─ iPhone (CAT004)")
    print("    └─ Android (CAT005)")
    print("  电脑 (CAT002)")
    print("  配件 (CAT003)")

    print("\n【热门商品】")
    print("  1. iPhone 15 Pro - ¥7,999 (库存50)")
    print("  2. MacBook Pro 14 - ¥12,999 (库存30)")
    print("  3. AirPods Pro - ¥1,999 (库存200)")

    print("\n【VIP客户】")
    print("  金卡: 张三(北京)、王五(深圳)")
    print("  银卡: 李四(上海)、钱七(杭州)")

    print("\n【订单统计】")
    print("  总订单: 10笔")
    print("  总金额: ¥83,987")
    print("  最大单笔: ¥12,999 (MacBook Pro)")

    # 4. 生成测试场景
    print("\n" + "=" * 70)
    print("测试场景建议")
    print("=" * 70)

    print("\n场景1: 基础查询")
    print("  用户: 查询所有iPhone产品")
    print("  预期: 2个产品 (iPhone 15 Pro, iPhone 15)")

    print("\n场景2: 反向导航")
    print("  用户: iPhone 15 Pro有哪些订单？")
    print("  预期: 3个订单 (O001, O002, O007)")

    print("\n场景3: 跨数据源Link")
    print("  用户: 金卡客户买了哪些商品？")
    print("  预期: 张三(iPhone 15 Pro, iPhone 15, MacBook Pro), 王五(MacBook Pro, AirPods Pro)")

    print("\n场景4: 多跳导航")
    print("  用户: 手机类目下被哪些VIP客户购买？")
    print("  预期: 金卡客户张三、银卡客户钱七")

    print("\n场景5: 聚合统计")
    print("  用户: 每个类目的销售额是多少？")
    print("  预期: 手机类目最高")

    print("\n场景6: 自引用Link")
    print("  用户: iPhone类目的父类目是什么？")
    print("  预期: 手机")

    print("\n" + "=" * 70)
    print("数据准备完成！可以开始前端测试")
    print("=" * 70)

    print("\n配置信息：")
    print("  MySQL数据库: test_shop.db (SQLite)")
    print("  Excel文件: test_customers.xlsx")
    print("  数据源配置: 需要在前端配置这两个数据源")


if __name__ == "__main__":
    create_test_data()
