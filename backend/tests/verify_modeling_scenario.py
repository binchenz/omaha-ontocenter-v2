#!/usr/bin/env python3
"""
End-to-end scenario: real user builds ontology from CSVs via chat, then queries it.

Phases:
  1. modeling — user uploads CSVs → agent infers ontology → user confirms
  2. query    — user asks business questions against the new ontology

Run from backend/:
    .venv/bin/python tests/verify_modeling_scenario.py
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


def build_csv_dataframes() -> dict[str, pd.DataFrame]:
    orders = pd.DataFrame([
        ("ORD-301", "C001", 15000, "已完成", "华东", "2026-03-05"),
        ("ORD-302", "C002", 28000, "已完成", "华东", "2026-03-10"),
        ("ORD-303", "C003", 12000, "已完成", "华东", "2026-03-15"),
        ("ORD-304", "C001",  8000, "已完成", "华东", "2026-03-18"),
        ("ORD-305", "C004", 22000, "已完成", "华东", "2026-03-22"),
        ("ORD-306", "C005",  6000, "已完成", "华东", "2026-03-25"),
        ("ORD-307", "C006", 18000, "已完成", "华北", "2026-03-08"),
        ("ORD-308", "C007",  9000, "已完成", "华北", "2026-03-12"),
        ("ORD-201", "C001", 11000, "已完成", "华东", "2026-02-03"),
        ("ORD-202", "C002", 25000, "已完成", "华东", "2026-02-12"),
        ("ORD-203", "C008", 13000, "已完成", "华东", "2026-02-20"),
    ], columns=["order_id", "customer_id", "amount", "status", "region", "created_at"])

    customers = pd.DataFrame([
        ("C001", "张三", "138-0001-0001", "华东", "VIP"),
        ("C002", "李四", "138-0002-0002", "华东", "VIP"),
        ("C003", "王五", "138-0003-0003", "华东", "普通"),
        ("C004", "赵六", "138-0004-0004", "华东", "VIP"),
        ("C005", "钱七", "138-0005-0005", "华东", "普通"),
        ("C006", "孙八", "138-0006-0006", "华北", "VIP"),
        ("C007", "周九", "138-0007-0007", "华北", "普通"),
        ("C008", "吴十", "138-0008-0008", "华东", "普通"),
    ], columns=["id", "name", "phone", "region", "level"])

    return {"orders": orders, "customers": customers}


async def main():
    db, project, user = setup_db(
        username="demo",
        email="demo@test.com",
        project_name="零售分析",
        project_description="Demo retail project",
    )
    uploaded = build_csv_dataframes()

    banner("Omaha OntoCenter — End-to-End 建模 + 查询 场景模拟")
    print(f"  项目: {project.name} (id={project.id}, setup_stage={project.setup_stage})")
    print(f"  数据: orders ({len(uploaded['orders'])} 行), customers ({len(uploaded['customers'])} 行)")
    print(f"  时间: {datetime.now().isoformat(timespec='seconds')}")

    from app.models.chat.chat_session import ChatSession
    session = ChatSession(project_id=project.id, user_id=user.id, title="建模与查询")
    db.add(session)
    db.commit()
    db.refresh(session)
    sid = session.id

    banner("Phase 1 · 建模会话")
    for turn in [
        "你好，我刚上传了订单和客户两份 CSV，请帮我把数据整理成业务对象。这是一个零售业务。",
        "看起来不错，请确认建模。",
    ]:
        render("user", turn)
        try:
            resp = await chat(project, db, sid, turn, uploaded_tables=uploaded)
        except Exception as e:
            print(f"\n   ❌ ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return
        render("assistant", resp["message"], resp.get("tool_calls"))
        db.refresh(project)
        print(f"\n   📌 setup_stage = {project.setup_stage}")

    db.refresh(project)
    if project.setup_stage != "ready":
        print(f"\n  ⚠️  本体未确认（stage={project.setup_stage}），跳过查询阶段")
        return

    with TempSqliteDB(uploaded) as db_path:
        project.omaha_config = build_omaha_yaml(db, project.tenant_id, db_path)
        db.commit()

        banner("Phase 2 · 查询会话（基于已确认本体）")
        for turn in [
            "我们现在有几个业务对象？",
            "华东地区有几个客户？",
            "上个月（2026年3月）华东地区金额超过1万的订单有多少？总金额是多少？",
        ]:
            render("user", turn)
            try:
                resp = await chat(project, db, sid, turn)
            except Exception as e:
                print(f"\n   ❌ ERROR: {type(e).__name__}: {e}")
                continue
            render("assistant", resp["message"], resp.get("tool_calls"))

        banner("Summary")
        from app.services.ontology.store import OntologyStore
        ont = OntologyStore(db).get_full_ontology(project.tenant_id)
        print(f"  ✅ 本体已建立：{len(ont['objects'])} 个对象")
        for o in ont["objects"]:
            print(f"     • {o['name']} (slug={o['slug']}) — {len(o['properties'])} 个字段")
        print(f"  ✅ 项目状态：{project.setup_stage}")


if __name__ == "__main__":
    asyncio.run(main())
