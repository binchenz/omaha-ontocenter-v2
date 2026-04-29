#!/usr/bin/env python3
"""
End-to-end scenario: real user builds ontology from CSVs via chat, then queries it.

Simulates 3 phases:
  Phase 1 (modeling): user uploads CSVs → agent infers ontology → user confirms
  Phase 2 (query):    user asks business questions against the new ontology

Uses a real LLM (DeepSeek). Run from backend/:
    .venv/bin/python tests/verify_modeling_scenario.py
"""
import asyncio
import os
import sys
import tempfile
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))


# ─── Mock CSV data ───────────────────────────────────────────────────────────

def build_csv_dataframes() -> dict[str, pd.DataFrame]:
    """Two realistic retail CSVs as pandas DataFrames."""
    orders = pd.DataFrame([
        # 3 月华东
        ("ORD-301", "C001", 15000, "已完成", "华东", "2026-03-05"),
        ("ORD-302", "C002", 28000, "已完成", "华东", "2026-03-10"),
        ("ORD-303", "C003", 12000, "已完成", "华东", "2026-03-15"),
        ("ORD-304", "C001",  8000, "已完成", "华东", "2026-03-18"),
        ("ORD-305", "C004", 22000, "已完成", "华东", "2026-03-22"),
        ("ORD-306", "C005",  6000, "已完成", "华东", "2026-03-25"),
        # 3 月华北
        ("ORD-307", "C006", 18000, "已完成", "华北", "2026-03-08"),
        ("ORD-308", "C007",  9000, "已完成", "华北", "2026-03-12"),
        # 2 月
        ("ORD-201", "C001", 11000, "已完成", "华东", "2026-02-03"),
        ("ORD-202", "C002", 25000, "已完成", "华东", "2026-02-12"),
        ("ORD-203", "C008", 13000, "已完成", "华东", "2026-02-20"),
    ], columns=["order_id", "customer_id", "amount", "status", "region", "created_at"])

    customers = pd.DataFrame([
        ("C001", "张三",  "138-0001-0001", "华东", "VIP"),
        ("C002", "李四",  "138-0002-0002", "华东", "VIP"),
        ("C003", "王五",  "138-0003-0003", "华东", "普通"),
        ("C004", "赵六",  "138-0004-0004", "华东", "VIP"),
        ("C005", "钱七",  "138-0005-0005", "华东", "普通"),
        ("C006", "孙八",  "138-0006-0006", "华北", "VIP"),
        ("C007", "周九",  "138-0007-0007", "华北", "普通"),
        ("C008", "吴十",  "138-0008-0008", "华东", "普通"),
    ], columns=["id", "name", "phone", "region", "level"])

    return {"orders": orders, "customers": customers}


# ─── DB setup ────────────────────────────────────────────────────────────────

def setup_database():
    """Create in-memory SQLite with all ORM tables, seed tenant + project."""
    from app.database import Base
    from app.models.auth.tenant import Tenant
    from app.models.auth.user import User
    from app.models.project.project import Project
    from app.core.security import get_password_hash
    import app.models  # noqa: F401 — registers all ORM classes

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    tenant = Tenant(name="demo")
    db.add(tenant)
    db.commit()

    user = User(
        username="demo",
        email="demo@test.com",
        hashed_password=get_password_hash("test"),
        tenant_id=tenant.id,
    )
    db.add(user)
    db.commit()

    project = Project(
        name="零售分析",
        description="Demo retail project",
        owner_id=user.id,
        tenant_id=tenant.id,
        setup_stage="modeling",  # already past upload+cleaning
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return db, project, user


# ─── Run a chat turn through ChatServiceV2 ───────────────────────────────────

async def chat(project, db, session_id: int, user_message: str,
               uploaded_tables: dict | None = None) -> dict[str, Any]:
    """Run one chat turn with optional uploaded_tables injection."""
    from app.services.agent.chat_service import ChatServiceV2
    from app.services.agent.tools.registry import ToolContext

    svc = ChatServiceV2(project=project, db=db)

    if uploaded_tables is not None:
        original = ToolContext.__init__

        def patched_init(self, **kw):
            original(self, **kw)
            self.uploaded_tables = uploaded_tables

        ToolContext.__init__ = patched_init  # type: ignore
        try:
            return await svc.send_message(session_id=session_id, user_message=user_message)
        finally:
            ToolContext.__init__ = original  # type: ignore
    return await svc.send_message(session_id=session_id, user_message=user_message)


def banner(text: str):
    print(f"\n{'═' * 78}\n  {text}\n{'═' * 78}")


def render_turn(role: str, content: str, tools: list | None = None):
    icon = "👤" if role == "user" else "🤖"
    print(f"\n{icon} {role.upper()}:")
    for line in content.split("\n"):
        print(f"   {line}")
    if tools:
        names = [t.get("name", "?") for t in tools]
        print(f"\n   🔧 调用工具: {' → '.join(names)}")


# ─── Scenario ────────────────────────────────────────────────────────────────

async def main():
    db, project, user = setup_database()
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

    # ─── Phase 1: 建模 ──────────────────────────────────────────────────────
    banner("Phase 1 · 建模会话")

    modeling_turns = [
        "你好，我刚上传了订单和客户两份 CSV，请帮我把数据整理成业务对象。这是一个零售业务。",
        "看起来不错，请确认建模。",
    ]

    for turn in modeling_turns:
        render_turn("user", turn)
        try:
            resp = await chat(project, db, sid, turn, uploaded_tables=uploaded)
        except Exception as e:
            print(f"\n   ❌ ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            return
        render_turn("assistant", resp["message"], resp.get("tool_calls"))

        db.refresh(project)
        print(f"\n   📌 setup_stage = {project.setup_stage}")

    # ─── Phase 2: 查询 ──────────────────────────────────────────────────────
    banner("Phase 2 · 查询会话（基于已确认本体）")

    db.refresh(project)
    if project.setup_stage != "ready":
        print(f"\n  ⚠️  本体未确认（stage={project.setup_stage}），跳过查询阶段")
        return

    project.omaha_config = _build_omaha_yaml(uploaded, db, project.tenant_id)
    db.commit()

    query_turns = [
        "我们现在有几个业务对象？",
        "华东地区有几个客户？",
        "上个月（2026年3月）华东地区金额超过1万的订单有多少？总金额是多少？",
    ]

    for turn in query_turns:
        render_turn("user", turn)
        try:
            resp = await chat(project, db, sid, turn)
        except Exception as e:
            print(f"\n   ❌ ERROR: {type(e).__name__}: {e}")
            continue
        render_turn("assistant", resp["message"], resp.get("tool_calls"))

    # ─── Summary ────────────────────────────────────────────────────────────
    banner("Summary")
    from app.services.ontology.store import OntologyStore
    ont = OntologyStore(db).get_full_ontology(project.tenant_id)
    print(f"  ✅ 本体已建立：{len(ont['objects'])} 个对象")
    for o in ont["objects"]:
        print(f"     • {o['name']} (slug={o['slug']}) — {len(o['properties'])} 个字段")
    print(f"  ✅ 项目状态：{project.setup_stage}")


def _build_omaha_yaml(uploaded: dict[str, pd.DataFrame], db, tenant_id: int) -> str:
    """Materialize the uploaded DataFrames to a SQLite file and emit an
    omaha_config YAML that mirrors the ontology objects already persisted
    by confirm_ontology, so OmahaService can resolve object_type → table."""
    import yaml
    from app.services.ontology.store import OntologyStore

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    import sqlite3
    conn = sqlite3.connect(tmp.name)
    for name, df in uploaded.items():
        df.to_sql(name, conn, if_exists="replace", index=False)
    conn.close()

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

    config = {
        "datasources": [
            {"id": "upload", "type": "sqlite", "connection": {"database": tmp.name}}
        ],
        "ontology": {"objects": objects_yaml},
    }
    return yaml.safe_dump(config, allow_unicode=True, sort_keys=False)


if __name__ == "__main__":
    asyncio.run(main())
