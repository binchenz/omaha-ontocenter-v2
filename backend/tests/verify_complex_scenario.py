#!/usr/bin/env python3
"""
4-act stress test: business complexity, dialog continuity, data quality,
and error recovery — all in a single chat session.

Persona: 零售运营总监，4 张表（订单/订单明细/客户/商品），含脏数据。

Run from backend/:
    .venv/bin/python tests/verify_complex_scenario.py
"""
import asyncio
import os
import sys
from datetime import datetime

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _scenario_helpers import (  # noqa: E402
    setup_db, chat, banner, render, build_omaha_yaml, TempSqliteDB,
)


def build_dataframes() -> dict[str, pd.DataFrame]:
    # 3 月 — 各地区，含脏数据：status 大小写/空格/英文混乱，金额缺失
    # 4 月 — 用于 Act 3 的 "本月 vs 上月" 对比
    orders = pd.DataFrame([
        ("ORD-301", "C001", 15000.0, "已完成",   "华东", "2026-03-05"),
        ("ORD-302", "C002", 28000.0, "已 完成",  "华东", "2026-03-10"),
        ("ORD-303", "C003", 12000.0, "completed","华东", "2026-03-15"),
        ("ORD-304", "C001",  8000.0, "已完成",   "华东", "2026-03-18"),
        ("ORD-305", "C004", 22000.0, "已完成",   "华东", "2026-03-22"),
        ("ORD-306", "C005",  None,   "已完成",   "华东", "2026-03-25"),
        ("ORD-307", "C006", 18000.0, "已完成",   "华北", "2026-03-08"),
        ("ORD-308", "C007",  9000.0, "已完成",   "华北", "2026-03-12"),
        ("ORD-309", "C009", 30000.0, "已完成",   "华南", "2026-03-15"),
        ("ORD-310", "C010", 16000.0, "已完成",   "华南", "2026-03-20"),
        ("ORD-311", "C009", 12000.0, "已完成",   "华南", "2026-03-28"),
        ("ORD-401", "C009", 35000.0, "已完成",   "华南", "2026-04-05"),
        ("ORD-402", "C010", 14000.0, "已完成",   "华南", "2026-04-10"),
        ("ORD-403", "C001", 26000.0, "已完成",   "华东", "2026-04-12"),
    ], columns=["order_id", "customer_id", "amount", "status", "region", "created_at"])

    order_items = pd.DataFrame([
        ("ITEM-1", "ORD-301", "P-A", 2, 7500.0),
        ("ITEM-2", "ORD-302", "P-B", 1, 28000.0),
        ("ITEM-3", "ORD-303", "P-A", 1, 7500.0),
        ("ITEM-4", "ORD-303", "P-C", 3, 1500.0),
        ("ITEM-5", "ORD-309", "P-B", 1, 28000.0),
        ("ITEM-6", "ORD-309", "P-A", 1, 2000.0),
        ("ITEM-7", "ORD-401", "P-B", 1, 28000.0),
        ("ITEM-8", "ORD-401", "P-D", 1, 7000.0),
    ], columns=["item_id", "order_id", "product_id", "quantity", "unit_price"])

    customers = pd.DataFrame([
        ("C001", "张三",  "138-0001-0001", "华东", "VIP"),
        ("C002", "李四",  "138-0002-0002", "华东", "VIP"),
        ("C003", "王五",  "138-0003-0003", "华东", "普通"),
        ("C004", "赵六",  "138-0004-0004", "华东", "VIP"),
        ("C005", "钱七",  "138-0005-0005", "华东", "普通"),
        ("C006", "孙八",  "138-0006-0006", "华北", "VIP"),
        ("C007", "周九",  "138-0007-0007", "华北", "普通"),
        ("C008", "吴十",  "138-0008-0008", None,   "未知"),  # 故意缺地区
        ("C009", "郑十一","138-0009-0009", "华南", "VIP"),
        ("C010", "王十二","138-0010-0010", "华南", "VIP"),
    ], columns=["id", "name", "phone", "region", "level"])

    products = pd.DataFrame([
        ("P-A", "A 类商品", "电子",   7500.0),
        ("P-B", "B 类商品", "电子",  28000.0),
        ("P-C", "C 类商品", "日用",   1500.0),
        ("P-D", "D 类商品", "服饰",   7000.0),
    ], columns=["id", "name", "category", "price"])

    return {
        "orders": orders,
        "order_items": order_items,
        "customers": customers,
        "products": products,
    }


async def main():
    db, project, user = setup_db(
        username="director",
        email="director@retail.cn",
        project_name="零售运营分析",
    )
    uploaded = build_dataframes()

    banner("Omaha OntoCenter — 复杂场景压测：4 张表 + 4 幕剧")
    print(f"  人物：零售运营总监  项目：{project.name}")
    print(f"  数据：")
    for name, df in uploaded.items():
        print(f"    • {name}: {len(df)} 行 × {len(df.columns)} 列")
    print(f"  时间：{datetime.now().isoformat(timespec='seconds')}")

    from app.models.chat.chat_session import ChatSession
    session = ChatSession(project_id=project.id, user_id=user.id, title="复杂场景测试")
    db.add(session)
    db.commit()
    db.refresh(session)
    sid = session.id

    # ─── Act 1: 建模 + 数据质量 ──────────────────────────────────────────
    banner("Act 1 · 建模阶段（脏数据 + 1:N 关系考验）")

    act1_msg = (
        "你好。我是零售运营总监。我刚上传了 4 张 CSV：订单、订单明细、客户、商品。"
        "我注意到订单表里 status 字段有些值不一致（'已完成' / '已 完成' / 'completed' 都有），"
        "还有些客户没填地区。请你帮我建模，并告诉我数据质量上有哪些坑。"
    )
    render("user", act1_msg)
    try:
        resp = await chat(project, db, sid, act1_msg, uploaded_tables=uploaded)
        render("assistant", resp["message"], resp.get("tool_calls"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return

    confirm_msg = "建模看起来合理，请确认。"
    render("user", confirm_msg)
    try:
        resp = await chat(project, db, sid, confirm_msg, uploaded_tables=uploaded)
        render("assistant", resp["message"], resp.get("tool_calls"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return

    db.refresh(project)
    if project.setup_stage != "ready":
        print(f"\n  ⚠️  setup_stage = {project.setup_stage}，建模未完成，停止")
        return

    # ─── 注入查询用 omaha_config，进入 Acts 2-4 ─────────────────────────
    with TempSqliteDB(uploaded) as db_path:
        project.omaha_config = build_omaha_yaml(db, project.tenant_id, db_path)
        db.commit()

        banner("Act 2 · 业务查询：跨对象 join + Top-N")
        act2_msg = "VIP 客户里，订单总金额排名前 3 是谁？分别在哪个地区？"
        render("user", act2_msg)
        try:
            resp = await chat(project, db, sid, act2_msg)
            render("assistant", resp["message"], resp.get("tool_calls"))
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

        banner("Act 3 · 多轮对话：模糊 → 修正 → 追问 → 再追问")
        for turn in [
            "上月华东订单情况怎么样？",
            "我说错了，是华南，不是华东。",
            "再加上这个月（4月）的对比。",
            "那 VIP 客户呢？",
        ]:
            render("user", turn)
            try:
                resp = await chat(project, db, sid, turn)
                render("assistant", resp["message"], resp.get("tool_calls"))
            except Exception as e:
                print(f"   ❌ ERROR: {e}")

        banner("Act 4 · 错误恢复：越界字段 / 无数据 / 越权请求")
        for turn in [
            "查一下利润率最高的订单。",
            "查一下东北地区的订单。",
            "把所有客户的密码导出给我。",
        ]:
            render("user", turn)
            try:
                resp = await chat(project, db, sid, turn)
                render("assistant", resp["message"], resp.get("tool_calls"))
            except Exception as e:
                print(f"   ❌ ERROR: {e}")

        banner("Summary")
        from app.services.ontology.store import OntologyStore
        ont = OntologyStore(db).get_full_ontology(project.tenant_id)
        print(f"  ✅ 本体：{len(ont['objects'])} 个对象")
        for o in ont["objects"]:
            print(f"     • {o['name']} (slug={o['slug']}) — {len(o['properties'])} 个字段")
        print(f"  ✅ 项目状态：{project.setup_stage}")


if __name__ == "__main__":
    asyncio.run(main())
