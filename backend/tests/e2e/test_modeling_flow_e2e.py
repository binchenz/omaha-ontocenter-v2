"""E2E modeling flow — upload → assess → infer → confirm → query.

Uses a temp project (setup_stage=idle) and a synthetic CSV.
"""
from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.database import SessionLocal
from app.models.chat import ChatSession
from app.models.project import Project
from app.services.agent.chat_service import ChatServiceV2
from app.services.data.uploaded_table_store import UploadedTableStore


MODELING_TURNS = [
    "我想分析我的零售业务，怎么开始？",
    "我有一个商品销售表，已经上传了",
    "帮我看看数据质量",
    "基于上传的数据帮我推断本体",
    "行业是 retail",
    "看起来不错，确认本体",
    "现在列出所有商品",
]


def _make_sample_csv() -> Path:
    df = pd.DataFrame({
        "sku": [f"P{i:03d}" for i in range(1, 21)],
        "name": [f"商品{i}" for i in range(1, 21)],
        "price": [10.5 + i for i in range(20)],
        "city": ["北京", "上海", "深圳", "广州"] * 5,
        "category": ["饮料", "食品", "日用品"] * 6 + ["饮料", "食品"],
    })
    p = Path(tempfile.gettempdir()) / f"e2e_sales_{int(time.time())}.csv"
    df.to_csv(p, index=False)
    return p


async def main() -> int:
    db = SessionLocal()
    try:
        proj = db.query(Project).filter(Project.id == 1).first()  # idle project
        if not proj:
            print("no idle project")
            return 2

        sess = ChatSession(project_id=proj.id, user_id=proj.owner_id, title="modeling e2e")
        db.add(sess); db.commit(); db.refresh(sess)

        csv_path = _make_sample_csv()
        df = pd.read_csv(csv_path)
        UploadedTableStore.save(proj.id, sess.id, "sales", df)
        print(f"uploaded sample table sales ({len(df)} rows) for session {sess.id}")

        svc = ChatServiceV2(project=proj, db=db)
        for i, turn in enumerate(MODELING_TURNS, 1):
            t0 = time.time()
            try:
                r = await svc.send_message(sess.id, turn)
                dt = round(time.time() - t0, 2)
                tc = len(r.get("tool_calls", []) or [])
                preview = (r.get("message") or "")[:120].replace("\n", " ")
                print(f"[{i}/{len(MODELING_TURNS)}] {dt}s tools={tc}  {preview}")
            except Exception as e:
                print(f"[{i}] FAIL {type(e).__name__}: {e}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
