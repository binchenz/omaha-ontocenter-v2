"""E2E edge cases — empty/long/special chars, SQL injection, compound queries."""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.database import SessionLocal
from app.models.chat import ChatSession
from app.models.project import Project
from app.services.agent.chat_service import ChatServiceV2

PROJECT_ID = 10

EDGE_CASES = [
    ("empty-prompt", "  "),
    ("long-prompt", "我想知道" + "非常详细的" * 50 + "商品信息"),
    ("special-chars", "查询 sku='P001' 的商品 (注意：含特殊字符 & < > )"),
    ("sql-injection", "'; DROP TABLE products; --"),
    ("emoji", "🛒 列出商品 📊"),
    ("compound-query", "列出深圳的商品，按价格排序，只看前 5 个，并显示成本"),
    ("compound-w-condition", "价格在 10 到 50 之间且类目是饮料的商品"),
    ("negation", "非深圳的商品有哪些？"),
    ("comparison", "哪个商品比平均价格贵？"),
    ("trend-question", "商品价格的分布是怎样的？"),
]


async def main() -> int:
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == PROJECT_ID).first()
        sess = ChatSession(project_id=PROJECT_ID, user_id=project.owner_id, title="edge")
        db.add(sess); db.commit(); db.refresh(sess)
        svc = ChatServiceV2(project=project, db=db)
        passed = 0
        for name, prompt in EDGE_CASES:
            t0 = time.time()
            try:
                r = await svc.send_message(sess.id, prompt)
                msg = r.get("message") or ""
                ok = bool(msg.strip())
                dt = round(time.time() - t0, 2)
                mark = "PASS" if ok else "FAIL"
                if ok: passed += 1
                print(f"  {mark}  {dt}s  [{name}] {msg[:80]!r}")
            except Exception as e:
                print(f"  ERR  [{name}] {type(e).__name__}: {str(e)[:120]}")
        print(f"\n=== {passed}/{len(EDGE_CASES)} passed ===")
        return 0 if passed == len(EDGE_CASES) else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
