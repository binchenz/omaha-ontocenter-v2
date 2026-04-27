"""E2E multi-turn context retention."""
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

CONVERSATIONS = [
    {"name": "refer-back-by-pronoun", "turns": [("价格最高的 3 个商品", ["price"]), ("它们在哪些城市销售？", ["city"])]},
    {"name": "narrow-then-broaden", "turns": [("深圳的商品有哪些？", ["深圳"]), ("那北京呢？", ["北京"]), ("加上上海一起列出来", ["上海"])]},
    {"name": "correction", "turns": [("列出所有商品价格", ["price"]), ("刚才的查询，再加上类目字段", ["category"])]},
    {"name": "followup-aggregation", "turns": [("展示前 10 个商品", []), ("这些商品里最贵的是哪个？", ["price"])]},
]


async def main() -> int:
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == PROJECT_ID).first()
        svc = ChatServiceV2(project=project, db=db)
        all_pass = True
        for conv in CONVERSATIONS:
            sess = ChatSession(project_id=PROJECT_ID, user_id=project.owner_id, title=conv["name"])
            db.add(sess); db.commit(); db.refresh(sess)
            print(f"\n=== {conv['name']} ===")
            for turn_idx, (prompt, expect_kw) in enumerate(conv["turns"], 1):
                t0 = time.time()
                r = await svc.send_message(sess.id, prompt)
                dt = round(time.time() - t0, 2)
                msg = (r.get("message") or "")
                hits = [k for k in expect_kw if k.lower() in msg.lower()]
                ok = (not expect_kw) or hits
                mark = "PASS" if ok else "FAIL"
                if not ok:
                    all_pass = False
                print(f"  [{turn_idx}] {mark}  {dt}s  '{prompt}' → {msg[:120]!r}")
        return 0 if all_pass else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
