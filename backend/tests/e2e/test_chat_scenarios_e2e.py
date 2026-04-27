"""E2E chat suite — basic / intermediate / complex scenarios via real LLM.

Usage: python -m tests.e2e.test_chat_scenarios_e2e
Uses project 10 (setup_stage=ready, has Stock + DailyQuote + Industry).
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e._env import ensure_test_db, is_provider_error

ensure_test_db()

from app.database import SessionLocal
from app.models.chat import ChatSession
from app.models.project import Project
from app.services.agent.chat_service import ChatServiceV2

PROJECT_ID = 10


@dataclass
class Scenario:
    name: str
    prompt: str
    expect_keywords: list[str] = field(default_factory=list)
    expect_tool_calls: bool = True


SCENARIOS: list[Scenario] = [
    # === 基础 ===
    Scenario("basic-greeting", "你好，介绍一下你能做什么", expect_tool_calls=False),
    Scenario("capability-question", "我能问你哪些问题？", expect_tool_calls=False),
    Scenario("list-objects", "我现在有哪些业务对象可以查询？"),
    Scenario("get-schema", "Stock 对象有哪些字段？", ["ts_code"], expect_tool_calls=False),
    Scenario("get-relationships", "Stock 和 DailyQuote 之间有什么关系？"),

    # === 进阶 ===
    Scenario("simple-query", "列出前 5 只股票的名称和行业"),
    Scenario("select-columns", "只显示股票代码和名称这两列，给我 10 条"),
    Scenario("filtered-query-cn", "查一下深圳的股票有哪些", ["深圳"]),
    Scenario("filtered-string", "行业是银行的股票有哪些？", ["银行"]),
    Scenario("filtered-multi", "深圳且行业是银行的股票"),
    Scenario("sorted-desc", "成交量最高的 5 只股票是哪些？"),
    Scenario("sorted-asc", "收盘价最低的 5 只股票"),
    Scenario("limit-only", "随便给我看 3 只股票"),

    # === 复杂 ===
    Scenario("aggregation-count", "每个行业有多少只股票？"),
    Scenario("aggregation-avg", "每个行业的平均涨跌幅是多少？"),
    Scenario("count-query", "一共有多少只股票？"),
    Scenario("multi-object", "帮我查一下平安银行的日线行情"),

    # === 异常 ===
    Scenario("unknown-object", "查询不存在的对象 XYZ 的数据", expect_tool_calls=False),
    Scenario("unknown-field", "列出股票的 nonexistent_field 字段", expect_tool_calls=False),
    Scenario("ambiguous", "帮我看看市场情况", expect_tool_calls=False),
    Scenario("empty-result", "涨跌幅大于 100% 的股票有哪些？"),
    Scenario("out-of-scope", "今天天气怎么样？", expect_tool_calls=False),

    # === 元能力 ===
    Scenario("chinese-english-mix", "show me top 5 stocks by volume"),
    Scenario("clarification", "再多看几个", expect_tool_calls=False),
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
            "name": sc.name, "prompt": sc.prompt,
            "elapsed": round(elapsed, 2), "passed": passed,
            "tool_calls": len(tool_calls),
            "keyword_hits": keyword_hits,
            "expected_keywords": sc.expect_keywords,
            "reply_preview": msg[:160],
        }
    except Exception as e:
        if is_provider_error(e):
            return {"name": sc.name, "prompt": sc.prompt,
                    "elapsed": round(time.time() - t0, 2),
                    "passed": False, "provider_error": f"{type(e).__name__}: {e}"}
        return {"name": sc.name, "prompt": sc.prompt,
                "elapsed": round(time.time() - t0, 2),
                "passed": False, "error": f"{type(e).__name__}: {e}"}


async def main() -> int:
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == PROJECT_ID).first()
        if not project:
            print(f"project {PROJECT_ID} not found"); return 2
        svc = ChatServiceV2(project=project, db=db)
        results = []
        for sc in SCENARIOS:
            # Fresh session per scenario to avoid context pollution
            sess = ChatSession(project_id=PROJECT_ID, user_id=project.owner_id, title=f"e2e-{sc.name}")
            db.add(sess); db.commit(); db.refresh(sess)
            print(f"\n>>> {sc.name}: {sc.prompt}")
            r = await run_scenario(svc, sess.id, sc)
            mark = "PASS" if r["passed"] else "FAIL"
            print(f"    {mark}  {r.get('elapsed')}s  tools={r.get('tool_calls', '?')}")
            if not r["passed"]:
                if "provider_error" in r:
                    print(f"    PROVIDER ERROR: {r['provider_error']}")
                else:
                    print(f"    reply: {r.get('reply_preview') or r.get('error')}")
            results.append(r)
        passed = sum(1 for r in results if r["passed"])
        provider_errors = sum(1 for r in results if "provider_error" in r)
        product_failures = len(results) - passed - provider_errors
        print(f"\n=== {passed}/{len(results)} passed ===")
        if provider_errors:
            print(
                f"  NOTE: {provider_errors} failures are PROVIDER ERRORS (502/transient from Anthropic). "
                "This is an infra/provider blockage, not a product regression."
            )
        if product_failures:
            print(f"  WARN: {product_failures} failures are product failures.")
        out = Path(__file__).parent / f"e2e_report_{int(time.time())}.json"
        out.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(f"report: {out}")
        return 0 if passed == len(results) else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
