# Agent Multi-Step Reasoning Enhancement — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve agent's ability to handle complex multi-step queries through prompt engineering and minimal code changes.

**Architecture:** No new modules except one tool file. Targeted modifications to existing components.

**Tech Stack:** FastAPI, SQLAlchemy, structlog. Tests use pytest with `.venv/bin/python`.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Create | `app/services/agent/tools/builtin/reasoning.py` | New `think` tool |
| Modify | `app/services/agent/tools/builtin/__init__.py` | Import reasoning module so `think` registers |
| Modify | `app/services/agent/skills/definitions/data_query.yaml` | Rewrite system prompt, add `think` to allowed_tools |
| Modify | `app/services/agent/tools/registry.py` | Add `meta` field to `ToolResult` |
| Modify | `app/services/agent/tools/view.py` | Populate `meta` in derived tool results |
| Modify | `app/services/agent/chat_service.py` | Raise `max_iterations` 8 → 12 |
| Modify | `app/services/agent/orchestrator/executor.py` | Better timeout message |
| Create | `tests/unit/agent/test_think_tool.py` | Test for `think` tool |
| Create | `tests/unit/agent/test_tool_result_meta.py` | Test for `meta` field |

---

### Task 1: Add `meta` field to `ToolResult`

**Files:**
- Modify: `backend/app/services/agent/tools/registry.py`
- Create: `backend/tests/unit/agent/test_tool_result_meta.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/unit/agent/test_tool_result_meta.py
from app.services.agent.tools.registry import ToolResult


class TestToolResultMeta:
    def test_to_dict_without_meta(self):
        r = ToolResult(success=True, data={"x": 1})
        assert r.to_dict() == {"success": True, "data": {"x": 1}, "error": None}

    def test_to_dict_with_meta(self):
        r = ToolResult(
            success=True,
            data={"rows": [1, 2, 3]},
            meta={"object_type": "order", "row_count": 3},
        )
        d = r.to_dict()
        assert d["meta"] == {"object_type": "order", "row_count": 3}
        assert d["success"] is True

    def test_meta_defaults_to_none(self):
        r = ToolResult(success=True)
        assert r.meta is None
        assert "meta" not in r.to_dict()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/unit/agent/test_tool_result_meta.py -v`
Expected: FAIL — `ToolResult` has no `meta` field.

- [ ] **Step 3: Implement the change in registry.py**

Modify the `ToolResult` dataclass in `app/services/agent/tools/registry.py`:

```python
@dataclass
class ToolResult:
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    meta: Optional[dict] = None

    def to_dict(self) -> dict:
        d = {"success": self.success, "data": self.data, "error": self.error}
        if self.meta:
            d["meta"] = self.meta
        return d
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/unit/agent/test_tool_result_meta.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 5: Run full suite for regressions**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/ --ignore=tests/e2e -q`
Expected: All pass (no regressions).

- [ ] **Step 6: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
git add app/services/agent/tools/registry.py tests/unit/agent/test_tool_result_meta.py
git commit -m "feat(agent): add meta field to ToolResult"
```

---

### Task 2: Populate `meta` in derived tool handlers

**Files:**
- Modify: `backend/app/services/agent/tools/view.py`

- [ ] **Step 1: Update `_execute_derived` to populate meta**

In `app/services/agent/tools/view.py`, locate the `_execute_derived` method (around line 132). After the query result is obtained and before each `ToolResult(success=True, ...)` return, build a meta dict and pass it.

For the search/count branch (around lines 199-205):

Replace:
```python
            if mode == "count":
                return ToolResult(
                    success=True,
                    data={"count": len(data), "data": data[:10]},
                )
            else:
                return ToolResult(success=True, data=result)
```

With:
```python
            meta = {
                "object_type": object_name,
                "object_slug": obj_slug,
                "row_count": len(data),
                "filters_applied": filters,
            }

            if mode == "count":
                return ToolResult(
                    success=True,
                    data={"count": len(data), "data": data[:10]},
                    meta=meta,
                )
            else:
                return ToolResult(success=True, data=result, meta=meta)
```

- [ ] **Step 2: Update `_execute_aggregate` to populate meta**

Locate the final `ToolResult` return in `_execute_aggregate` (around line 279). Add meta:

Find:
```python
        return ToolResult(
            success=True,
            data={...},
        )
```

Add a `meta` argument with `object_type`, `object_slug`, `group_by`, `metric`, `row_count` (after grouping).

If you cannot identify the exact return statement during implementation, read the full `_execute_aggregate` function (lines ~210-285) and add `meta` to the success-case return only. Do not change error returns.

- [ ] **Step 3: Run agent tests**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/unit/agent/ -q`
Expected: All pass.

- [ ] **Step 4: Run full suite**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/ --ignore=tests/e2e -q`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
git add app/services/agent/tools/view.py
git commit -m "feat(agent): populate meta in derived tool results"
```

---

### Task 3: Add `think` tool

**Files:**
- Create: `backend/app/services/agent/tools/builtin/reasoning.py`
- Modify: `backend/app/services/agent/tools/builtin/__init__.py` (if exists, otherwise verify auto-discovery)
- Create: `backend/tests/unit/agent/test_think_tool.py`

- [ ] **Step 1: Check how builtin tools are registered**

Read `backend/app/services/agent/tools/builtin/__init__.py`. If it explicitly imports tool modules (e.g., `from . import query, chart, ...`), the new `reasoning.py` must be added there. If it's empty and tools are auto-discovered, no change needed.

Also check `backend/app/services/agent/__init__.py` and `backend/app/services/agent/tools/__init__.py` to confirm registration mechanism.

- [ ] **Step 2: Write the failing test**

```python
# backend/tests/unit/agent/test_think_tool.py
import asyncio
from app.services.agent.tools.registry import ToolContext, global_registry
from app.services.agent.tools.builtin import reasoning  # noqa: F401 — ensures registration


class TestThinkTool:
    def test_think_is_registered(self):
        assert global_registry.has("think")

    def test_think_returns_success(self):
        ctx = ToolContext(db=None, omaha_service=None)
        result = asyncio.run(
            global_registry.execute("think", {"reasoning": "test plan"}, ctx)
        )
        assert result.success is True
        assert result.data == {"noted": True}

    def test_think_spec_has_required_reasoning(self):
        specs = {s.name: s for s in global_registry.get_specs()}
        spec = specs["think"]
        assert "reasoning" in spec.parameters["properties"]
        assert spec.parameters["required"] == ["reasoning"]
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/unit/agent/test_think_tool.py -v`
Expected: FAIL — `reasoning` module doesn't exist.

- [ ] **Step 4: Create the `think` tool**

Create `backend/app/services/agent/tools/builtin/reasoning.py`:

```python
"""Reasoning tools — let the LLM externalize its planning before acting."""
from app.services.agent.tools.registry import ToolContext, ToolResult, register_tool


@register_tool(
    name="think",
    description=(
        "在执行复杂查询前，用这个工具分析问题、制定查询计划。"
        "适用于多对象、多条件、对比、趋势类问题。简单查询可以跳过。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "你的分析和查询计划",
            }
        },
        "required": ["reasoning"],
    },
)
def think(params: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult(success=True, data={"noted": True})
```

- [ ] **Step 5: Wire up registration if needed**

If Step 1 found that `builtin/__init__.py` explicitly imports modules, add:
```python
from . import reasoning  # noqa: F401
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/unit/agent/test_think_tool.py -v`
Expected: All 3 tests PASS.

- [ ] **Step 7: Run full suite**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/ --ignore=tests/e2e -q`
Expected: All pass.

- [ ] **Step 8: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
git add app/services/agent/tools/builtin/reasoning.py app/services/agent/tools/builtin/__init__.py tests/unit/agent/test_think_tool.py
git commit -m "feat(agent): add think tool for explicit reasoning"
```

---

### Task 4: Rewrite `data_query.yaml` system prompt

**Files:**
- Modify: `backend/app/services/agent/skills/definitions/data_query.yaml`

- [ ] **Step 1: Replace the file content**

Replace the entire content of `backend/app/services/agent/skills/definitions/data_query.yaml` with:

```yaml
name: data_query
description: 数据查询与分析
trigger_keywords: ["查询", "多少", "分析", "趋势", "对比", "统计", "报表"]
system_prompt: |
  你是数据分析专家，帮助用户查询和分析业务数据。

  ## 查询策略

  简单问题（单对象、单条件）→ 直接调用 search_* 或 count_*
  复杂问题（多对象、多条件、对比、趋势）→ 先用 think 工具分析，再分步执行

  ## 使用 think 工具的时机

  当问题涉及以下情况时，先调用 think 分析：
  - 需要查询多个对象（如 Order + Customer）
  - 需要对比（如 本月 vs 上月）
  - 需要多步过滤（如 先筛地区，再筛金额）
  - 需要跨对象导航（如 某客户的所有订单）

  ## 工具使用规则

  1. 涉及具体数据的问题，必须先调用工具查询，不要编造数据
  2. 涉及聚合（每个/平均/总数/最大/最小）时优先使用 aggregate_* 工具
  3. 当用户说"它们"、"那些"、"刚才的查询再加个条件"时，使用 refine_objectset
  4. 查询返回空结果时，检查过滤条件是否过严，尝试放宽条件重新查询
  5. 如果数据触发健康规则阈值，主动提醒

  ## 回答格式

  - 先给出直接结论（数字、趋势、判断）
  - 再补充关键数据支撑
  - 如果做了多步查询，简要说明分析路径
  - 对比类问题要给出变化幅度（百分比）

  ## 示例

  用户: "上个月华东地区高客单订单有多少？"
  推荐步骤:
  1. think: 需要查 Order 对象，过滤条件为 region=华东、created_at=上月、amount>高客单阈值
  2. search_order(region="华东", created_at_min="2026-03-01", created_at_max="2026-03-31", amount_min=10000)
  3. 基于结果回答

  用户: "跟上上月比呢？"
  推荐步骤:
  1. think: 用户在追问对比，需要查上上月同条件数据
  2. search_order(region="华东", created_at_min="2026-02-01", created_at_max="2026-02-28", amount_min=10000)
  3. 对比两个月数据，计算变化幅度

allowed_tools:
  - think
  - search_*
  - count_*
  - aggregate_*
  - refine_objectset
  - query_data
  - list_objects
  - get_schema
  - get_relationships
  - generate_chart
  - auto_chart
  - save_asset
  - list_assets
  - get_lineage
  - screen_stocks
```

- [ ] **Step 2: Verify YAML loads correctly**

Run a quick sanity check:
```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -c "
from app.services.agent.skills.loader import SkillLoader
loader = SkillLoader()
skill = loader.get('data_query')
assert skill is not None
assert 'think' in skill.allowed_tools
assert '查询策略' in skill.system_prompt
print('OK')
"
```
Expected: `OK`

- [ ] **Step 3: Run agent tests**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/unit/agent/ -q`
Expected: All pass.

- [ ] **Step 4: Run full suite**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/ --ignore=tests/e2e -q`
Expected: All pass.

- [ ] **Step 5: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
git add app/services/agent/skills/definitions/data_query.yaml
git commit -m "feat(agent): rewrite data_query prompt with planning guidance"
```

---

### Task 5: Raise max_iterations and improve timeout message

**Files:**
- Modify: `backend/app/services/agent/chat_service.py`
- Modify: `backend/app/services/agent/orchestrator/executor.py`

- [ ] **Step 1: Find and update max_iterations in chat_service.py**

In `backend/app/services/agent/chat_service.py`, find the `ExecutorAgent(...)` instantiation. Currently passes `max_iterations=8` (or relies on the default of 8).

Change to `max_iterations=12`. If currently using the default, explicitly pass it:
```python
executor = ExecutorAgent(provider=provider, registry=view, max_iterations=12)
```

- [ ] **Step 2: Update timeout message in executor.py**

In `backend/app/services/agent/orchestrator/executor.py`, find the "Max iterations reached" return at the bottom of `run()` (around line 130-137):

Replace:
```python
        return AgentResponse(
            message="抱歉，处理超时。",
            tool_calls=tool_call_log,
            data_table=data_table,
            chart_config=chart_config,
            sql=sql,
        )
```

With:
```python
        return AgentResponse(
            message="分析步骤较多，已达到最大轮次。以上是目前的分析结果，如需继续请追问。",
            tool_calls=tool_call_log,
            data_table=data_table,
            chart_config=chart_config,
            sql=sql,
        )
```

- [ ] **Step 3: Run full suite**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/ --ignore=tests/e2e -q`
Expected: All pass.

- [ ] **Step 4: Commit**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend
git add app/services/agent/chat_service.py app/services/agent/orchestrator/executor.py
git commit -m "feat(agent): raise max_iterations to 12, improve timeout message"
```

---

### Task 6: Final Verification

- [ ] **Step 1: Verify `think` tool is reachable end-to-end**

Run a quick smoke test:
```bash
cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -c "
from app.services.agent.tools.registry import global_registry
import app.services.agent.tools.builtin  # triggers all registrations
assert global_registry.has('think'), 'think tool not registered'
specs = {s.name: s for s in global_registry.get_specs()}
print('think description:', specs['think'].description[:50])
print('Total registered tools:', len(specs))
"
```
Expected: Prints description and count.

- [ ] **Step 2: Run the full test suite**

Run: `cd /Users/wangfushuaiqi/omaha_ontocenter/backend && .venv/bin/python -m pytest tests/ --ignore=tests/e2e -q`
Expected: All pass with no regressions.

- [ ] **Step 3: Tag**

```bash
cd /Users/wangfushuaiqi/omaha_ontocenter
git tag agent-reasoning-phase1-complete
```