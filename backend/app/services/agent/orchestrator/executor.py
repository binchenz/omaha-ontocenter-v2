"""ExecutorAgent — ReAct loop (think → act → observe → answer)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional, List, Dict, Union

from app.services.agent.providers.base import ProviderAdapter, ToolSpec
from app.services.agent.tools.registry import ToolRegistry, ToolContext
from app.services.agent.runtime.conversation import ConversationRuntime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json_dumps(obj: Any) -> str:
    """JSON serialize with Decimal support."""
    def default(o: Any) -> Any:
        if isinstance(o, Decimal):
            return float(o)
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(obj, ensure_ascii=False, default=default)


# ---------------------------------------------------------------------------
# AgentResponse
# ---------------------------------------------------------------------------

@dataclass
class AgentResponse:
    message: str
    tool_calls: list[dict] = field(default_factory=list)
    data_table: list[dict] | None = None
    chart_config: Optional[dict] = None
    sql: Optional[str] = None
    structured: list[dict] | None = None
    setup_stage: Optional[str] = None


# ---------------------------------------------------------------------------
# ExecutorAgent
# ---------------------------------------------------------------------------

class ExecutorAgent:
    def __init__(
        self,
        provider: ProviderAdapter,
        registry: ToolRegistry,
        max_iterations: int = 8,
    ) -> None:
        self.provider = provider
        self.registry = registry
        self.max_iterations = max_iterations

    async def run(self, runtime: ConversationRuntime, ctx: ToolContext) -> AgentResponse:
        """Run the ReAct loop and return an AgentResponse."""
        skill = runtime.skill
        allowed_tools = skill.allowed_tools or []

        # Get tool specs filtered by skill's allowed_tools
        tool_specs: list[ToolSpec] = self.registry.get_specs(
            whitelist=allowed_tools if allowed_tools else None
        )
        has_tools = bool(tool_specs)

        data_table: list[dict] | None = None
        chart_config: Optional[dict] = None
        sql: Optional[str] = None
        tool_call_log: list[dict] = []
        force_answer = False

        for _iteration in range(self.max_iterations):
            # Determine tool_choice
            tool_choice = "none" if force_answer else "auto"

            messages = runtime.get_messages_for_llm()
            llm_response = await self.provider.send(
                messages=messages,
                tools=tool_specs if has_tools else None,
                tool_choice=tool_choice,
            )

            # No tool calls → final answer
            if not llm_response.tool_calls:
                final_text = llm_response.content or ""
                cleaned, structured = ConversationRuntime.extract_structured(final_text)
                return AgentResponse(
                    message=cleaned,
                    tool_calls=tool_call_log,
                    data_table=data_table,
                    chart_config=chart_config,
                    sql=sql,
                    structured=structured,
                )

            # Append assistant message with tool calls
            runtime.append_assistant_message(
                content=llm_response.content,
                tool_calls=llm_response.tool_calls,
                reasoning_content=llm_response.reasoning_content,
            )

            # Execute each tool call
            for tc in llm_response.tool_calls:
                result = await self.registry.execute(tc.name, tc.arguments, ctx)
                result_dict = result.to_dict()
                result_str = _json_dumps(result_dict)

                # Capture data_table, sql, chart_config from query_data
                if tc.name == "query_data" and result.success and result.data:
                    rows = result.data.get("data")
                    if rows:
                        data_table = rows
                        sql = result.data.get("sql")
                        force_answer = True

                # Capture chart_config from chart tools
                if tc.name in ("generate_chart", "auto_chart") and result.success and result.data:
                    chart_config = result.data.get("chart_config") or result.data

                # Build tool call log entry
                summary = result_str[:500]
                tool_call_log.append({
                    "name": tc.name,
                    "params": tc.arguments,
                    "result_summary": summary,
                })

                runtime.append_tool_result(tc.id, result_str)

        # Max iterations reached
        return AgentResponse(
            message="抱歉，处理超时。",
            tool_calls=tool_call_log,
            data_table=data_table,
            chart_config=chart_config,
            sql=sql,
        )
