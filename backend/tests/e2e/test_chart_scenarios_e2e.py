"""E2E chart/visualization scenarios — verify chart tools get invoked."""
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

CHART_PROMPTS = [
    ("bar-chart", "用柱状图展示前 5 个商品的价格"),
    ("pie-chart", "用饼图展示各城市的商品占比"),
    ("line-chart", "画一个商品价格的折线图"),
    ("auto-chart", "帮我可视化一下商品数据"),
    ("chart-w-filter", "深圳商品的价格分布，用图表展示"),
]


async def main() -> int:
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == PROJECT_ID).first()
        svc = ChatServiceV2(project=project, db=db)
        passed = 0
        for name, prompt in CHART_PROMPTS:
            sess = ChatSession(project_id=PROJECT_ID, user_id=project.owner_id, title=name)
            db.add(sess); db.commit(); db.refresh(sess)
            t0 = time.time()
            try:
                r = await svc.send_message(sess.id, prompt)
                tool_names = [tc.get("name", "") for tc in (r.get("tool_calls") or [])]
                has_chart = any("chart" in n for n in tool_names)
                dt = round(time.time() - t0, 2)
                mark = "PASS" if has_chart else "FAIL"
                if has_chart: passed += 1
                print(f"  {mark}  {dt}s  [{name}] tools={tool_names}")
            except Exception as e:
                print(f"  ERR  [{name}] {type(e).__name__}: {str(e)[:120]}")
        print(f"\n=== {passed}/{len(CHART_PROMPTS)} passed ===")
        return 0 if passed == len(CHART_PROMPTS) else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
