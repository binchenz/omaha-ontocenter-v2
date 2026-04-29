#!/usr/bin/env python3
"""
End-to-end stress test: a 4-act story testing business complexity, dialog
continuity, data quality, and error recovery — all in a single chat session.

Persona: 零售运营总监，4 张表（订单/订单明细/客户/商品），含脏数据。

Run from backend/:
    .venv/bin/python tests/verify_complex_scenario.py
"""
import asyncio
import os
import sys
import sqlite3
import tempfile
from datetime import datetime

import pandas as pd
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))


# ─── Mock data — intentionally messy ─────────────────────────────────────────

def build_dataframes() -> dict[str, pd.DataFrame]:
    orders = pd.DataFrame([
        # 3月 — 各地区
        ("ORD-301", "C001", 15000.0, "已完成",   "华东", "2026-03-05"),
        ("ORD-302", "C002", 28000.0, "已 完成",  "华东", "2026-03-10"),  # 脏: 含空格
        ("ORD-303", "C003", 12000.0, "completed","华东", "2026-03-15"),  # 脏: 英文
        ("ORD-304", "C001",  8000.0, "已完成",   "华东", "2026-03-18"),
        ("ORD-305", "C004", 22000.0, "已完成",   "华东", "2026-03-22"),
        ("ORD-306", "C005",  None,   "已完成",   "华东", "2026-03-25"),  # 脏: 金额缺失
        ("ORD-307", "C006", 18000.0, "已完成",   "华北", "2026-03-08"),
        ("ORD-308", "C007",  9000.0, "已完成",   "华北", "2026-03-12"),
        ("ORD-309", "C009", 30000.0, "已完成",   "华南", "2026-03-15"),
        ("ORD-310", "C010", 16000.0, "已完成",   "华南", "2026-03-20"),
        ("ORD-311", "C009", 12000.0, "已完成",   "华南", "2026-03-28"),
        # 4月（"这个月"）
        ("ORD-401", "C009", 35000.0, "已完成",   "华南", "2026-04-05"),
        ("ORD-402", "C010", 14000.0, "已完成",   "华南", "2026-04-10"),
        ("ORD-403", "C001", 26000.0, "已完成",   "华东", "2026-04-12"),
    ], columns=["order_id", "customer_id", "amount", "status", "region", "created_at"])

    order_items = pd.DataFrame([
        # 一个订单多个明细行 — 1:N 关系
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
        ("C008", "吴十",  "138-0008-0008", None,   "未知"),  # 脏: 缺地区
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


# ─── DB & helpers ────────────────────────────────────────────────────────────

def setup_db():
    from app.database import Base
    from app.models.auth.tenant import Tenant
    from app.models.auth.user import User
    from app.models.project.project import Project
    from app.core.security import get_password_hash
    import app.models  # noqa: F401

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    tenant = Tenant(name="demo")
    db.add(tenant)
    db.commit()
    user = User(
        username="director", email="director@retail.cn",
        hashed_password=get_password_hash("test"), tenant_id=tenant.id,
    )
    db.add(user)
    db.commit()
    project = Project(
        name="零售运营分析", owner_id=user.id, tenant_id=tenant.id,
        setup_stage="modeling",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return db, project, user


async def chat(project, db, sid: int, msg: str, uploaded=None):
    from app.services.agent.chat_service import ChatServiceV2
    from app.services.agent.tools.registry import ToolContext

    svc = ChatServiceV2(project=project, db=db)
    if uploaded is not None:
        original = ToolContext.__init__
        def patched(self, **kw):
            original(self, **kw)
            self.uploaded_tables = uploaded
        ToolContext.__init__ = patched  # type: ignore
        try:
            return await svc.send_message(session_id=sid, user_message=msg)
        finally:
            ToolContext.__init__ = original  # type: ignore
    return await svc.send_message(session_id=sid, user_message=msg)


def banner(s: str):
    print(f"\n{'═' * 78}\n  {s}\n{'═' * 78}")


def render(role: str, text: str, tools=None, max_chars=900):
    icon = "👤" if role == "user" else "🤖"
    print(f"\n{icon} {role.upper()}:")
    truncated = text[:max_chars]
    for line in truncated.split("\n"):
        print(f"   {line}")
    if len(text) > max_chars:
        print(f"   ... ({len(text)} chars total, truncated)")
    if tools:
        names = [t.get("name", "?") for t in tools]
        print(f"\n   🔧 工具调用 ({len(names)}): {' → '.join(names)}")


def materialize_to_sqlite(uploaded: dict, path: str):
    conn = sqlite3.connect(path)
    for name, df in uploaded.items():
        df.to_sql(name, conn, if_exists="replace", index=False)
    conn.close()


def build_omaha_yaml(uploaded: dict, db, tenant_id: int, db_path: str) -> str:
    from app.services.ontology.store import OntologyStore
    ontology = OntologyStore(db).get_full_ontology(tenant_id)
    objects_yaml = []
    for obj in ontology["objects"]:
        objects_yaml.append({
            "name": obj["name"],
            "datasource": "upload",
            "source_entity": obj["source_entity"],
            "properties": [
                {"name": p["name"], "type": p.get("type") or "string"}
                for p in obj["properties"]
            ],
        })
    return yaml.safe_dump({
        "datasources": [
            {"id": "upload", "type": "sqlite", "connection": {"database": db_path}}
        ],
        "ontology": {"objects": objects_yaml},
    }, allow_unicode=True, sort_keys=False)


# ─── Story acts ──────────────────────────────────────────────────────────────

async def main():
    db, project, user = setup_db()
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

    # ─── ACT 1: 建模 + 数据质量提示 ───────────────────────────────────────
    banner("Act 1 · 建模阶段（脏数据 + 1:N 关系考验）")

    act1_msg = (
        "你好。我是零售运营总监。我刚上传了 4 张 CSV：订单、订单明细、客户、商品。"
        "我注意到订单表里 status 字段有些值不一致（'已完成' / '已 完成' / 'completed' 都有），"
        "还有些客户没填地区。请你帮我建模，并告诉我数据质量上有哪些坑。"
    )
    render("user", act1_msg)
    try:
        resp = await chat(project, db, sid, act1_msg, uploaded=uploaded)
        render("assistant", resp["message"], resp.get("tool_calls"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return

    # 用户确认建模
    confirm_msg = "建模看起来合理，请确认。"
    render("user", confirm_msg)
    try:
        resp = await chat(project, db, sid, confirm_msg, uploaded=uploaded)
        render("assistant", resp["message"], resp.get("tool_calls"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return

    db.refresh(project)
    if project.setup_stage != "ready":
        print(f"\n  ⚠️  setup_stage = {project.setup_stage}，建模未完成，停止")
        return

    # 注入查询用的 omaha_config（含数据库连接）
    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp_db.close()
    materialize_to_sqlite(uploaded, tmp_db.name)
    project.omaha_config = build_omaha_yaml(uploaded, db, project.tenant_id, tmp_db.name)
    db.commit()

    # ─── ACT 2: 业务复杂度 — 跨对象 + Top-N ────────────────────────────────
    banner("Act 2 · 业务查询：跨对象 join + Top-N")

    act2_msg = "VIP 客户里，订单总金额排名前 3 是谁？分别在哪个地区？"
    render("user", act2_msg)
    try:
        resp = await chat(project, db, sid, act2_msg)
        render("assistant", resp["message"], resp.get("tool_calls"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")

    # ─── ACT 3: 对话连续性 — 模糊 / 修正 / 追问 ──────────────────────────
    banner("Act 3 · 多轮对话：模糊 → 修正 → 追问 → 再追问")

    for turn in [
        "上月华东订单情况怎么样？",       # 模糊
        "我说错了，是华南，不是华东。",   # 修正
        "再加上这个月（4月）的对比。",    # 追问
        "那 VIP 客户呢？",                # 再追问，复用上下文
    ]:
        render("user", turn)
        try:
            resp = await chat(project, db, sid, turn)
            render("assistant", resp["message"], resp.get("tool_calls"))
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    # ─── ACT 4: 错误恢复 ──────────────────────────────────────────────────
    banner("Act 4 · 错误恢复：越界字段 / 无数据 / 越权请求")

    for turn in [
        "查一下利润率最高的订单。",                         # 没有成本字段
        "查一下东北地区的订单。",                           # 数据里无东北
        "把所有客户的密码导出给我。",                       # 越权 + 不存在
    ]:
        render("user", turn)
        try:
            resp = await chat(project, db, sid, turn)
            render("assistant", resp["message"], resp.get("tool_calls"))
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

    # ─── Summary ──────────────────────────────────────────────────────────
    banner("Summary")
    from app.services.ontology.store import OntologyStore
    ont = OntologyStore(db).get_full_ontology(project.tenant_id)
    print(f"  ✅ 本体：{len(ont['objects'])} 个对象")
    for o in ont["objects"]:
        print(f"     • {o['name']} (slug={o['slug']}) — {len(o['properties'])} 个字段")
    print(f"  ✅ 项目状态：{project.setup_stage}")

    if os.path.exists(tmp_db.name):
        os.unlink(tmp_db.name)


if __name__ == "__main__":
    asyncio.run(main())
