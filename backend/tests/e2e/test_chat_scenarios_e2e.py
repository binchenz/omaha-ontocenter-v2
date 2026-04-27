"""End-to-end chat scenarios — hits real LLM via ChatServiceV2.

Usage:  python -m tests.e2e.test_chat_scenarios_e2e

Uses project 10 (setup_stage=ready, has Product + GoodsMallMapping objects).
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.database import SessionLocal  # noqa: E402
from app.models.chat import ChatSession  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.services.agent.chat_service import ChatServiceV2  # noqa: E402

PROJECT_ID = 10


@dataclass
class Scenario:
    name: str
    prompt: str
    expect_keywords: list[str] = field(default_factory=list)
    expect_tool_calls: bool = True


SCENARIOS: list[Scenario] = [
    Scenario("basic-greeting", "你好，介绍一下你能做什么", expect_tool_calls=False),
    Scenario("list-objects", "我现在有哪些业务对象可以查询？", ["Product"], expect_tool_calls=True),
    Scenario("get-schema", "Product 对象有哪些字段？", ["sku", "price"], expect_tool_calls=True),
    Scenario("simple-query", "列出前 5 个商品的名称和价格", ["sku", "price"], expect_tool_calls=True),
    Scenario("filtered-query", "查一下深圳的商品有哪些", ["深圳"], expect_tool_calls=True),
    Scenario("sorted-query", "价格最高的 5 个商品是哪些？", ["price"], expect_tool_calls=True),
    Scenario("aggregation", "每个城市有多少个商品？", ["城市"], expect_tool_calls=True),
    Scenario("computation", "计算每个商品的毛利（价格 - 成本），列出前 5 个", ["毛利"], expect_tool_calls=True),
    Scenario("unknown-object", "查询不存在的对象 XYZ 的数据", [], expect_tool_calls=True),
    Scenario("ambiguous", "帮我看看销售情况", [], expect_tool_calls=False),
]


async def run_scenario(svc: ChatServiceV2, sess_id: int, sc: Scenario) -> dict:
    t0 = time.time()
    try:
        result = await svc.send_message(sess_id, sc.prompt)
        elapsed = time.time() - t0
        msg = result.get("message", "") or ""
        tool_calls = result.get("tool_calls", []) or []
        keyword_hits = [k for k in sc.expect_keywords if k.lower() in msg.lower()]
        passed = (
            (not sc.expect_tool_calls or len(tool_calls) > 0)
            and (not sc.expect_keywords or len(keyword_hits) > 0)
        )
        return {
            "name": sc.name,
            "prompt": sc.prompt,
            "elapsed": round(elapsed, 2),
            "passed": passed,
            "tool_calls": len(tool_calls),
            "keyword_hits": keyword_hits,
            "expected_keywords": sc.expect_keywords,
            "reply_preview": msg[:160],
        }
    except Exception as e:  # noqa: BLE001
        return {
            "name": sc.name,
            "prompt": sc.prompt,
            "elapsed": round(time.time() - t0, 2),
            "passed": False,
            "error": f"{type(e).__name__}: {e}",
        }


async def main() -> int:
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == PROJECT_ID).first()
        if not project:
            print(f"project {PROJECT_ID} not found")
            return 2

        sess = ChatSession(project_id=PROJECT_ID, user_id=project.owner_id, title="e2e suite")
        db.add(sess)
        db.commit()
        db.refresh(sess)

        svc = ChatServiceV2(project=project, db=db)

        results = []
        for sc in SCENARIOS:
            print(f"\n>>> {sc.name}: {sc.prompt}")
            r = await run_scenario(svc, sess.id, sc)
            print(f"    {'PASS' if r['passed'] else 'FAIL'}  {r.get('elapsed')}s  tools={r.get('tool_calls', '?')}")
            if not r["passed"]:
                print(f"    reply: {r.get('reply_preview') or r.get('error')}")
            results.append(r)

        passed = sum(1 for r in results if r["passed"])
        print(f"\n=== {passed}/{len(results)} passed ===")

        out = Path(__file__).parent / f"e2e_report_{int(time.time())}.json"
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"report: {out}")
        return 0 if passed == len(results) else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
