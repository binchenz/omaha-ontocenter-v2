"""E2E chat suite — basic / intermediate / complex scenarios via real LLM.

Usage: python -m tests.e2e.test_chat_scenarios_e2e
Uses project 10 (setup_stage=ready, has Product + GoodsMallMapping).
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.e2e._env import ensure_test_db, is_provider_error, ProviderError

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
    Scenario("list-objects", "我现在有哪些业务对象可以查询？", ["Product"]),
    Scenario("get-schema", "Product 对象有哪些字段？", ["sku", "price"]),
    Scenario("get-relationships", "Product 和 GoodsMallMapping 之间有什么关系？"),

    # === 进阶 ===
    Scenario("simple-query", "列出前 5 个商品的名称和价格", ["sku"]),
    Scenario("select-columns", "只显示商品名称和城市这两列，给我 10 条", ["city"]),
    Scenario("filtered-query-cn", "查一下深圳的商品有哪些", ["深圳"]),
    Scenario("filtered-numeric", "价格大于 30 元的商品有哪些？"),
    Scenario("filtered-multi", "深圳且价格大于 20 元的商品", ["深圳"]),
    Scenario("sorted-desc", "价格最高的 5 个商品是哪些？"),
    Scenario("sorted-asc", "价格最低的 5 个商品"),
    Scenario("limit-only", "随便给我看 3 个商品"),

    # === 复杂 ===
    Scenario("aggregation-count", "每个城市有多少个商品？", ["城市"]),
    Scenario("aggregation-avg", "每个城市的商品平均价格是多少？"),
    Scenario("computation", "计算每个商品的毛利（价格-成本），列出前 5 个", ["毛利"]),
    Scenario("computation-rate", "哪些商品的毛利率低于 20%？", ["毛利"]),
    Scenario("top-n-by-margin", "毛利率最高的 3 个商品", ["毛利"]),

    # === 异常 ===
    Scenario("unknown-object", "查询不存在的对象 XYZ 的数据"),
    Scenario("unknown-field", "列出商品的 nonexistent_field 字段"),
    Scenario("ambiguous", "帮我看看销售情况", expect_tool_calls=False),
    Scenario("empty-result", "价格大于一百万的商品有哪些？"),
    Scenario("out-of-scope", "今天天气怎么样？", expect_tool_calls=False),

    # === 元能力 ===
    Scenario("chinese-english-mix", "show me top 5 products by price", ["price"]),
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
        sess = ChatSession(project_id=PROJECT_ID, user_id=project.owner_id, title="e2e suite")
        db.add(sess); db.commit(); db.refresh(sess)
        svc = ChatServiceV2(project=project, db=db)
        results = []
        for sc in SCENARIOS:
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
