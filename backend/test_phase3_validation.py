#!/usr/bin/env python
"""
Phase 3: Ontology 重新设计数据验证和端到端测试
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal
from app.models.project import Project
from app.services.omaha import omaha_service
from app.services.semantic import semantic_service

# 测试结果收集
test_results = {
    "timestamp": datetime.now().isoformat(),
    "tests": []
}

def log_test(name, status, details=None, error=None):
    """记录测试结果"""
    result = {
        "name": name,
        "status": status,  # "PASS", "FAIL", "SKIP"
        "details": details,
        "error": error
    }
    test_results["tests"].append(result)

    status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⏭️"
    print(f"\n{status_icon} {name}")
    if details:
        print(f"   {details}")
    if error:
        print(f"   错误: {error}")

def update_project_config():
    """更新 project 7 的配置为新的 ontology_redesign_v2.yaml"""
    print("=" * 80)
    print("步骤 1: 更新 Project 7 配置")
    print("=" * 80)

    config_path = Path(__file__).parent.parent / "docs" / "superpowers" / "ontology_redesign_v2.yaml"

    if not config_path.exists():
        log_test("更新配置", "FAIL", error=f"配置文件不存在: {config_path}")
        return False

    with open(config_path, 'r', encoding='utf-8') as f:
        new_config = f.read()

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == 7).first()
        if not project:
            log_test("更新配置", "FAIL", error="Project 7 不存在")
            return False

        project.omaha_config = new_config
        db.commit()

        log_test("更新配置", "PASS", f"已更新 Project 7 配置 ({len(new_config)} 字符)")
        return True
    except Exception as e:
        db.rollback()
        log_test("更新配置", "FAIL", error=str(e))
        return False
    finally:
        db.close()

def test_object_queries():
    """测试对象查询"""
    print("\n" + "=" * 80)
    print("步骤 2: 验证对象查询")
    print("=" * 80)

    # 获取配置
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == 7).first()
        if not project or not project.omaha_config:
            log_test("获取配置", "FAIL", error="Project 7 配置不存在")
            return
        config = project.omaha_config
    finally:
        db.close()

    # 测试对象列表
    test_objects = [
        ("Product", "主数据对象"),
        ("Category", "使用 query 字段的维度对象"),
        ("City", "使用 query 字段的维度对象"),
        ("Platform", "使用 query 字段的维度对象"),
        ("ProductPrice", "城市+日期粒度的事实对象"),
        ("ProductCost", "城市+日期粒度的事实对象"),
        ("CompetitorPrice", "城市+平台+日期粒度的事实对象"),
    ]

    for obj_name, description in test_objects:
        try:
            result = omaha_service.query_objects(
                config_yaml=config,
                object_type=obj_name,
                limit=5
            )

            if result.get("success"):
                data = result.get("data", [])
                sql = result.get("sql", "")
                log_test(
                    f"查询 {obj_name}",
                    "PASS",
                    f"{description} - 返回 {len(data)} 条记录"
                )
                print(f"   SQL: {sql[:100]}...")
                if data:
                    print(f"   示例数据: {json.dumps(data[0], ensure_ascii=False, default=str)[:200]}...")
            else:
                log_test(
                    f"查询 {obj_name}",
                    "FAIL",
                    error=result.get("error", "未知错误")
                )
        except Exception as e:
            log_test(f"查询 {obj_name}", "FAIL", error=str(e))

def test_relationships():
    """测试关系 JOIN"""
    print("\n" + "=" * 80)
    print("步骤 3: 验证关系 JOIN")
    print("=" * 80)

    # 获取配置
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == 7).first()
        if not project or not project.omaha_config:
            log_test("获取配置", "FAIL", error="Project 7 配置不存在")
            return
        config = project.omaha_config
    finally:
        db.close()

    # 测试关系列表
    test_cases = [
        {
            "name": "Product -> ProductPrice",
            "object": "ProductPrice",
            "fields": ["ProductPrice.sku_id", "ProductPrice.city", "ProductPrice.ppy_price", "Product.sku_name"],
            "description": "商品价格关联商品信息"
        },
        {
            "name": "ProductPrice -> ProductCost (跨粒度)",
            "object": "ProductPrice",
            "fields": ["ProductPrice.sku_id", "ProductPrice.city", "ProductPrice.ppy_price", "ProductCost.ppy_current_cost"],
            "description": "价格和成本关联（相同粒度）"
        },
        {
            "name": "ProductPrice -> CompetitorPrice (跨粒度)",
            "object": "ProductPrice",
            "fields": ["ProductPrice.sku_id", "ProductPrice.city", "ProductPrice.ppy_price", "CompetitorPrice.mall_price", "CompetitorPrice.platform_name"],
            "description": "价格和竞品价格关联（不同粒度）"
        },
    ]

    for test_case in test_cases:
        try:
            result = omaha_service.query_objects(
                config_yaml=config,
                object_type=test_case["object"],
                selected_columns=test_case["fields"],
                limit=5
            )

            if result.get("success"):
                data = result.get("data", [])
                sql = result.get("sql", "")
                log_test(
                    test_case["name"],
                    "PASS",
                    f"{test_case['description']} - 返回 {len(data)} 条记录"
                )
                print(f"   SQL: {sql[:150]}...")
                if data:
                    print(f"   示例数据: {json.dumps(data[0], ensure_ascii=False, default=str)[:200]}...")
            else:
                log_test(
                    test_case["name"],
                    "FAIL",
                    error=result.get("error", "未知错误")
                )
        except Exception as e:
            log_test(test_case["name"], "FAIL", error=str(e))

def test_computed_fields():
    """测试计算字段"""
    print("\n" + "=" * 80)
    print("步骤 4: 验证计算字段")
    print("=" * 80)

    # 获取配置
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == 7).first()
        if not project or not project.omaha_config:
            log_test("获取配置", "FAIL", error="Project 7 配置不存在")
            return
        config = project.omaha_config
    finally:
        db.close()

    test_cases = [
        {
            "name": "ProductPrice.effective_price",
            "object": "ProductPrice",
            "fields": ["ProductPrice.sku_id", "ProductPrice.ppy_price", "ProductPrice.ppy_promotion_price", "ProductPrice.effective_price"],
            "description": "有效售价（促销价优先）"
        },
        {
            "name": "CompetitorPrice.price_gap_percentage",
            "object": "CompetitorPrice",
            "fields": ["CompetitorPrice.sku_id", "CompetitorPrice.price_gap", "CompetitorPrice.mall_price", "CompetitorPrice.price_gap_percentage"],
            "description": "价差百分比"
        },
    ]

    for test_case in test_cases:
        try:
            result = omaha_service.query_objects(
                config_yaml=config,
                object_type=test_case["object"],
                selected_columns=test_case["fields"],
                limit=5
            )

            if result.get("success"):
                data = result.get("data", [])
                sql = result.get("sql", "")
                log_test(
                    test_case["name"],
                    "PASS",
                    f"{test_case['description']} - 返回 {len(data)} 条记录"
                )
                print(f"   SQL: {sql[:150]}...")
                if data:
                    print(f"   示例数据: {json.dumps(data[0], ensure_ascii=False, default=str)[:200]}...")
            else:
                log_test(
                    test_case["name"],
                    "FAIL",
                    error=result.get("error", "未知错误")
                )
        except Exception as e:
            log_test(test_case["name"], "FAIL", error=str(e))

def test_agent_context():
    """测试 Agent 上下文"""
    print("\n" + "=" * 80)
    print("步骤 5: 验证 Agent 上下文")
    print("=" * 80)

    # 获取配置
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == 7).first()
        if not project or not project.omaha_config:
            log_test("获取配置", "FAIL", error="Project 7 配置不存在")
            return
        config = project.omaha_config
    finally:
        db.close()

    try:
        # 解析配置
        semantic_result = semantic_service.parse_config(config)

        if not semantic_result.get("valid"):
            log_test("Agent 上下文包含新特性", "FAIL", error=semantic_result.get("error", "配置解析失败"))
            return

        objects = semantic_result.get("objects", {})
        if not objects:
            log_test("Agent 上下文包含新特性", "FAIL", error="没有找到对象定义")
            return

        # 构建完整的 Agent 上下文
        context_lines = []
        for obj_name, obj_meta in objects.items():
            agent_ctx = semantic_service.build_agent_context(obj_meta)
            context_lines.append(f"### {obj_name}\n{agent_ctx}")

        full_context = "\n\n".join(context_lines)

        # 检查是否包含粒度信息
        has_granularity = "数据粒度" in full_context
        # 检查是否包含业务上下文
        has_business_context = "业务上下文" in full_context

        if has_granularity and has_business_context:
            log_test(
                "Agent 上下文包含新特性",
                "PASS",
                f"包含粒度信息和业务上下文 (总长度: {len(full_context)} 字符, {len(objects)} 个对象)"
            )
            # 打印部分上下文
            print(f"\n   上下文示例 (前 800 字符):")
            print(f"   {full_context[:800]}...")
        else:
            log_test(
                "Agent 上下文包含新特性",
                "FAIL",
                error=f"缺少特性 - 粒度: {has_granularity}, 业务上下文: {has_business_context}"
            )
    except Exception as e:
        import traceback
        log_test("Agent 上下文包含新特性", "FAIL", error=f"{str(e)}\n{traceback.format_exc()}")

def generate_report():
    """生成测试报告"""
    print("\n" + "=" * 80)
    print("测试报告")
    print("=" * 80)

    total = len(test_results["tests"])
    passed = sum(1 for t in test_results["tests"] if t["status"] == "PASS")
    failed = sum(1 for t in test_results["tests"] if t["status"] == "FAIL")
    skipped = sum(1 for t in test_results["tests"] if t["status"] == "SKIP")

    print(f"\n总计: {total} 个测试")
    print(f"✅ 通过: {passed}")
    print(f"❌ 失败: {failed}")
    print(f"⏭️  跳过: {skipped}")

    if failed > 0:
        print("\n失败的测试:")
        for test in test_results["tests"]:
            if test["status"] == "FAIL":
                print(f"  - {test['name']}: {test['error']}")

    # 保存报告
    report_path = Path(__file__).parent.parent / "docs" / "superpowers" / "plans" / "phase3-validation-report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(test_results, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n详细报告已保存到: {report_path}")

    return failed == 0

def main():
    """主函数"""
    print("Ontology 重新设计 - Phase 3 数据验证和端到端测试")
    print("=" * 80)

    # 步骤 1: 更新配置
    if not update_project_config():
        print("\n❌ 配置更新失败，终止测试")
        return False

    # 步骤 2: 验证对象查询
    test_object_queries()

    # 步骤 3: 验证关系 JOIN
    test_relationships()

    # 步骤 4: 验证计算字段
    test_computed_fields()

    # 步骤 5: 验证 Agent 上下文
    test_agent_context()

    # 生成报告
    success = generate_report()

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
