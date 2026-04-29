# Agent Multi-Step Reasoning Enhancement

Date: 2026-04-29
Status: Approved
Scope: Improve agent's ability to decompose and execute complex multi-step queries

## Problem

The current agent handles simple single-step queries well ("茅台今天收盘价") but struggles with complex questions that require multiple steps ("华东地区上月高客单订单有多少，跟上上月比变化如何"). The system prompt lacks query planning guidance, the ReAct loop caps at 8 iterations (too few for multi-step), and there's no mechanism for the LLM to explicitly reason before acting.

## Solution

Four targeted changes, no architectural overhaul:

1. Add a `think` tool for explicit reasoning
2. Rewrite `data_query.yaml` system prompt with planning guidance and few-shot examples
3. Standardize tool result format for easier intermediate result composition
4. Raise max_iterations from 8 to 12

## 1. `think` Tool

A no-op tool that lets the LLM externalize its reasoning before executing queries.

Location: `backend/app/services/agent/tools/builtin/reasoning.py`

```python
@register_tool(
    name="think",
    description="在执行复杂查询前，用这个工具分析问题、制定查询计划。输入你的推理过程。",
    parameters={
        "type": "object",
        "properties": {
            "reasoning": {
                "type": "string",
                "description": "你的分析和查询计划"
            }
        },
        "required": ["reasoning"]
    }
)
def think(params: dict, ctx: ToolContext) -> ToolResult:
    return ToolResult(success=True, data={"noted": True})
```

Add `think` to `data_query.yaml` allowed_tools list.

Why this matters:
- Forces LLM to plan before acting on complex queries
- Reasoning is captured in tool_call_log (auditable)
- Simple queries can skip it (not mandatory)
- Zero cost — no DB or API calls

## 2. Rewrite `data_query.yaml` System Prompt

Current prompt is 8 lines, too terse. Replace with structured guidance.

New `data_query.yaml`:

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

## 3. Standardize Tool Result Format

Current `ToolResult.to_dict()` returns `{"success": bool, "data": dict, "error": str}`. The `data` dict varies wildly between tools.

Add a `meta` field to ToolResult for context that helps the LLM compose results:

```python
@dataclass
class ToolResult:
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    meta: Optional[dict] = None  # NEW: object_type, row_count, filters_applied

    def to_dict(self) -> dict:
        d = {"success": self.success, "data": self.data, "error": self.error}
        if self.meta:
            d["meta"] = self.meta
        return d
```

Update the derived tool handlers (search_*, count_*, aggregate_*) in `tools/view.py` to populate meta:

```python
meta = {
    "object_type": object_type,
    "row_count": len(rows),
    "filters_applied": [f.to_dict() for f in obj_set.filters],
}
return ToolResult(success=True, data={"data": rows}, meta=meta)
```

This gives the LLM structured context about what each query returned, making it easier to reason about combining results.

## 4. Raise max_iterations

In `backend/app/services/agent/chat_service.py`, change:

```python
ExecutorAgent(provider=provider, registry=view, max_iterations=12)
```

Also update the timeout message in `executor.py` to be more helpful:

```python
return AgentResponse(
    message="分析步骤较多，已达到最大轮次。以上是目前的分析结果，如需继续请追问。",
    ...
)
```

## Files Changed

| Action | File | Change |
|--------|------|--------|
| Create | `app/services/agent/tools/builtin/reasoning.py` | `think` tool |
| Modify | `app/services/agent/skills/definitions/data_query.yaml` | Rewrite system prompt |
| Modify | `app/services/agent/tools/registry.py` | Add `meta` field to ToolResult |
| Modify | `app/services/agent/tools/view.py` | Populate meta in derived tool handlers |
| Modify | `app/services/agent/chat_service.py` | max_iterations 8 → 12 |
| Modify | `app/services/agent/orchestrator/executor.py` | Better timeout message |
| Create | `tests/unit/agent/test_think_tool.py` | Test for think tool |
| Create | `tests/unit/agent/test_tool_result_meta.py` | Test for meta field |

## Out of Scope

- Plan-then-Execute architecture (future consideration if prompt-based approach insufficient)
- compose_results tool (LLM handles summarization in natural language)
- Intent classification / smart routing (separate initiative)
- Memory / cross-session context (separate initiative)
- Streaming support (separate initiative)

## Success Criteria

- Agent can answer "华东地区上月高客单订单有多少" in ≤4 tool calls
- Agent can handle follow-up "跟上上月比呢" using context from previous answer
- Agent uses `think` tool for complex queries, skips it for simple ones
- Tool results include meta with object_type and row_count
- No regression in simple query performance
