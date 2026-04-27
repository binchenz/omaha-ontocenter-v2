"""E2E concurrency / latency — N parallel sessions, measure p50/p95."""
from __future__ import annotations

import asyncio
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.database import SessionLocal
from app.models.chat import ChatSession
from app.models.project import Project
from app.services.agent.chat_service import ChatServiceV2

PROJECT_ID = 10
CONCURRENCY = 5
PROMPTS = ["列出 5 个商品", "价格最高的商品", "深圳的商品", "商品总数", "显示商品名和价格"]


async def one_call(svc: ChatServiceV2, db, project, prompt: str) -> float:
    sess = ChatSession(project_id=PROJECT_ID, user_id=project.owner_id, title="perf")
    db.add(sess); db.commit(); db.refresh(sess)
    t0 = time.time()
    try:
        await svc.send_message(sess.id, prompt)
        return time.time() - t0
    except Exception as e:
        print(f"  ERR {type(e).__name__}: {str(e)[:80]}")
        return -1.0


async def main() -> int:
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == PROJECT_ID).first()
        svc = ChatServiceV2(project=project, db=db)
        print(f"running {CONCURRENCY} parallel calls...")
        tasks = [one_call(svc, db, project, PROMPTS[i % len(PROMPTS)]) for i in range(CONCURRENCY)]
        latencies = await asyncio.gather(*tasks)
        ok = sorted(x for x in latencies if x > 0)
        if not ok:
            print("all calls failed"); return 1
        print(f"\n=== latency over {len(ok)}/{CONCURRENCY} calls ===")
        print(f"  min:  {min(ok):.2f}s")
        print(f"  p50:  {statistics.median(ok):.2f}s")
        print(f"  p95:  {ok[max(0, int(len(ok)*0.95)-1)]:.2f}s")
        print(f"  max:  {max(ok):.2f}s")
        print(f"  mean: {statistics.mean(ok):.2f}s")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
