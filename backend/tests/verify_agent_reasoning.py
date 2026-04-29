#!/usr/bin/env python3
"""
Agent Reasoning Verification — simulates real user queries against mock retail data.

Usage:
    cd backend && .venv/bin/python tests/verify_agent_reasoning.py
"""
import asyncio
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime
from unittest.mock import MagicMock

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"))


# ─── 1. Create mock SQLite data ──────────────────────────────────────────────

def create_mock_db(db_path: str):
    """Create a SQLite DB with realistic retail data."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    c.execute("""CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT,
        amount REAL,
        status TEXT,
        region TEXT,
        created_at TEXT
    )""")

    c.execute("""CREATE TABLE customers (
        id TEXT PRIMARY KEY,
        name TEXT,
        phone TEXT,
        region TEXT,
        level TEXT
    )""")

    # 模拟 3 月（上月）和 2 月（上上月）的订单
    orders = [
        # 3月华东 — 高客单（>10000）
        ("ORD-301", "C001", 15000, "已完成", "华东", "2026-03-05"),
        ("ORD-302", "C002", 28000, "已完成", "华东", "2026-03-10"),
        ("ORD-303", "C003", 12000, "已完成", "华东", "2026-03-15"),
        ("ORD-304", "C001", 8000,  "已完成", "华东", "2026-03-18"),   # 低客单
        ("ORD-305", "C004", 22000, "已完成", "华东", "2026-03-22"),
        ("ORD-306", "C005", 6000,  "已完成", "华东", "2026-03-25"),   # 低客单
        # 3月华北
        ("ORD-307", "C006", 18000, "已完成", "华北", "2026-03-08"),
        ("ORD-308", "C007", 9000,  "已完成", "华北", "2026-03-12"),
        # 2月华东 — 高客单
        ("ORD-201", "C001", 11000, "已完成", "华东", "2026-02-03"),
        ("ORD-202", "C002", 25000, "已完成", "华东", "2026-02-12"),
        ("ORD-203", "C008", 13000, "已完成", "华东", "2026-02-20"),
        ("ORD-204", "C003", 7500,  "已完成", "华东", "2026-02-25"),   # 低客单
        # 2月华北
        ("ORD-205", "C006", 14000, "已完成", "华北", "2026-02-10"),
    ]

    customers = [
        ("C001", "张三", "138-0001-0001", "华东", "VIP"),
        ("C002", "李四", "138-0002-0002", "华东", "VIP"),
        ("C003", "王五", "138-0003-0003", "华东", "普通"),
        ("C004", "赵六", "138-0004-0004", "华东", "VIP"),
        ("C005", "钱七", "138-0005-0005", "华东", "普通"),
        ("C006", "孙八", "138-0006-0006", "华北", "VIP"),
        ("C007", "周九", "138-0007-0007", "华北", "普通"),
        ("C008", "吴十", "138-0008-0008", "华东", "普通"),
    ]

    c.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)
    c.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)
    conn.commit()
    conn.close()


# ─── 2. Build YAML ontology config ───────────────────────────────────────────

def build_yaml_config(db_path: str) -> str:
    return f"""
datasources:
  - id: retail_db
    type: sqlite
    connection:
      database: {db_path}

ontology:
  objects:
    - name: 订单
      slug: ding-dan
      datasource: retail_db
      source_entity: orders
      primary_key: order_id
      properties:
        - name: order_id
          slug: order-id
          column: order_id
          type: string
          semantic_type: order_id
        - name: customer_id
          slug: customer-id
          column: customer_id
          type: string
          semantic_type: customer_id
        - name: amount
          slug: amount
          column: amount
          type: number
          semantic_type: currency_cny
        - name: status
          slug: status
          column: status
          type: string
        - name: region
          slug: region
          column: region
          type: string
          semantic_type: region
        - name: created_at
          slug: created-at
          column: created_at
          type: string
          semantic_type: datetime

    - name: 客户
      slug: ke-hu
      datasource: retail_db
      source_entity: customers
      primary_key: id
      properties:
        - name: id
          slug: id
          column: id
          type: string
          semantic_type: customer_id
        - name: name
          slug: name
          column: name
          type: string
          semantic_type: person_name
        - name: phone
          slug: phone
          column: phone
          type: string
        - name: region
          slug: region
          column: region
          type: string
          semantic_type: region
        - name: level
          slug: level
          column: level
          type: string
"""


# ─── 3. Build ontology context (mimics OntologyStore.get_full_ontology) ──────

def build_ontology_context() -> dict:
    inner = {
        "objects": [
            {
                "name": "订单",
                "slug": "ding-dan",
                "source_entity": "orders",
                "datasource_id": "retail_db",
                "datasource_type": "sqlite",
                "description": "客户订单",
                "business_context": "零售订单",
                "domain": "retail",
                "properties": [
                    {"name": "order_id", "slug": "order-id", "type": "string", "semantic_type": "order_id"},
                    {"name": "customer_id", "slug": "customer-id", "type": "string", "semantic_type": "customer_id"},
                    {"name": "amount", "slug": "amount", "type": "number", "semantic_type": "currency_cny"},
                    {"name": "status", "slug": "status", "type": "string"},
                    {"name": "region", "slug": "region", "type": "string", "semantic_type": "region"},
                    {"name": "created_at", "slug": "created-at", "type": "string", "semantic_type": "datetime"},
                ],
                "health_rules": [],
                "goals": [],
                "knowledge": [],
            },
            {
                "name": "客户",
                "slug": "ke-hu",
                "source_entity": "customers",
                "datasource_id": "retail_db",
                "datasource_type": "sqlite",
                "description": "客户档案",
                "business_context": "客户信息",
                "domain": "retail",
                "properties": [
                    {"name": "id", "slug": "id", "type": "string", "semantic_type": "customer_id"},
                    {"name": "name", "slug": "name", "type": "string", "semantic_type": "person_name"},
                    {"name": "phone", "slug": "phone", "type": "string"},
                    {"name": "region", "slug": "region", "type": "string", "semantic_type": "region"},
                    {"name": "level", "slug": "level", "type": "string"},
                ],
                "health_rules": [],
                "goals": [],
                "knowledge": [],
            },
        ],
        "relationships": [],
    }
    # view.py expects ctx.ontology_context["ontology"]["objects"] — wrap accordingly.
    # factory.build() reads top-level "objects" — so include both forms.
    return {"objects": inner["objects"], "relationships": inner["relationships"], "ontology": inner}


# ─── 4. Run agent queries ────────────────────────────────────────────────────

async def run_query(provider, skill, ontology_context, omaha_service, query: str, history: list):
    """Run a single query through ExecutorAgent and return structured results."""
    from app.services.agent.runtime.conversation import ConversationRuntime
    from app.services.agent.runtime import session_store
    from app.services.agent.tools.registry import global_registry, ToolContext
    from app.services.agent.tools.view import ToolRegistryView
    from app.services.agent.tools.factory import ObjectTypeToolFactory
    from app.services.agent.orchestrator.executor import ExecutorAgent

    runtime = ConversationRuntime(skill=skill)
    runtime.build_system_prompt(ontology_context)

    # Load history
    for msg in history:
        if msg["role"] == "user":
            runtime.append_user_message(msg["content"])
        elif msg["role"] == "assistant":
            runtime.append_assistant_message(content=msg["content"], tool_calls=None)

    runtime.append_user_message(query)

    derived_specs = ObjectTypeToolFactory().build(ontology_context)
    tool_view = ToolRegistryView(builtin=global_registry, derived=derived_specs)

    ctx = ToolContext(
        db=None,
        omaha_service=omaha_service,
        tenant_id=1,
        project_id=1,
        session_id=1,
        ontology_context=ontology_context,
        session_store=session_store,
    )

    executor = ExecutorAgent(provider=provider, registry=tool_view, max_iterations=12)
    response = await executor.run(runtime, ctx)

    return {
        "query": query,
        "answer": response.message,
        "tool_calls": response.tool_calls,
        "data_table": response.data_table,
        "iterations": len(response.tool_calls),
    }


async def main():
    # Setup
    tmp = tempfile.mkdtemp()
    db_path = os.path.join(tmp, "retail_test.db")
    create_mock_db(db_path)
    config_yaml = build_yaml_config(db_path)
    ontology_context = build_ontology_context()

    # Build services
    from app.services.legacy.financial.omaha import OmahaService
    from app.services.agent.chat_service import ProviderFactory
    from app.services.agent.skills.loader import SkillLoader

    omaha_service = OmahaService(config_yaml)
    provider = ProviderFactory.create()
    loader = SkillLoader()
    skill = loader.load("data_query")

    print("=" * 80)
    print("  Agent Reasoning Verification")
    print(f"  Provider: {provider.__class__.__name__}")
    print(f"  DB: {db_path}")
    print(f"  Time: {datetime.now().isoformat()}")
    print("=" * 80)

    # 测试用例
    test_cases = [
        {
            "name": "Case 1: 简单查询 — 不应该用 think",
            "query": "华东地区有几个客户？",
            "expect_think": False,
            "history": [],
        },
        {
            "name": "Case 2: 复杂查询 — 应该用 think",
            "query": "上个月（2026年3月）华东地区金额超过1万的订单有多少？总金额是多少？",
            "expect_think": True,
            "history": [],
        },
        {
            "name": "Case 3: 追问对比 — 应该用 think",
            "query": "跟2月比，华东地区高客单（>1万）订单数量变化如何？",
            "expect_think": True,
            "history": [],
        },
        {
            "name": "Case 4: 聚合查询 — aggregate 优先",
            "query": "各地区的订单总金额分别是多少？",
            "expect_think": False,
            "history": [],
        },
    ]

    all_results = []
    conversation_history = []

    for tc in test_cases:
        print(f"\n{'─' * 70}")
        print(f"  {tc['name']}")
        print(f"  Query: {tc['query']}")
        print(f"{'─' * 70}")

        history = tc.get("history", conversation_history.copy())

        try:
            result = await run_query(provider, skill, ontology_context, omaha_service, tc["query"], history)
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            result = {"query": tc["query"], "answer": f"ERROR: {e}", "tool_calls": [], "iterations": 0}
            all_results.append(result)
            continue

        # Analyze tool calls
        tool_names = [t["name"] for t in result["tool_calls"]]
        used_think = "think" in tool_names
        iterations = result["iterations"]

        # Check expectations
        think_ok = used_think == tc["expect_think"]
        think_status = "✅" if think_ok else "⚠️"

        print(f"\n  {think_status} think used: {used_think} (expected: {tc['expect_think']})")
        print(f"  📊 Tool calls ({iterations}): {' → '.join(tool_names) if tool_names else 'none'}")
        print(f"\n  💬 Answer:")
        for line in result["answer"][:500].split("\n"):
            print(f"     {line}")
        if len(result["answer"]) > 500:
            print(f"     ... ({len(result['answer'])} chars total)")

        # Update conversation history for follow-up tests
        conversation_history.append({"role": "user", "content": tc["query"]})
        conversation_history.append({"role": "assistant", "content": result["answer"]})

        all_results.append(result)

    # Summary
    print(f"\n{'=' * 80}")
    print("  Summary")
    print(f"{'=' * 80}")
    for i, (tc, r) in enumerate(zip(test_cases, all_results)):
        tools = [t["name"] for t in r["tool_calls"]]
        think_ok = ("think" in tools) == tc["expect_think"]
        status = "✅" if think_ok and not r["answer"].startswith("ERROR") else "❌"
        print(f"  {status} Case {i+1}: {tc['name']}")
        print(f"     Tools: {' → '.join(tools)}")
        print(f"     Answer preview: {r['answer'][:80]}...")
    print()

    # Clean up
    os.unlink(db_path)
    os.rmdir(tmp)


if __name__ == "__main__":
    asyncio.run(main())
