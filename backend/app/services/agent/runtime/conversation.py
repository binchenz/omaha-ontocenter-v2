"""ConversationRuntime: manages message history and system prompt assembly."""
from __future__ import annotations

import json
import re
from typing import Any

from app.services.agent.skills.loader import Skill
from app.services.agent.providers.base import Message, ToolCall

_BASE_TEMPLATE = """\
你是一个企业数据分析助手，帮助用户接入数据、整理语义、回答业务问题。
你的目标用户是中小企业的非技术人员，请始终用业务语言回答，避免技术术语。

{skill_prompt}

## 可用数据对象
{ontology_context}

## 工作方式（ReAct）
你必须遵循 思考→行动→观察→回答 的循环：
1. **思考**：分析用户意图，判断当前应该接入数据、清洗数据、确认建模、还是查询数据
2. **行动**：调用合适的工具
3. **观察**：分析工具返回结果
4. **回答**：用业务语言给出简洁结论

## 强制规则
- 任何涉及具体数据的问题，必须先调用工具查询，不得凭空回答
- 如果查询结果为空或不符合预期，直接告知用户，不要编造数据
- 查询一次后立即基于结果回答，不要反复查询
"""


class ConversationRuntime:
    def __init__(self, skill: Skill) -> None:
        self.skill = skill
        self.messages: list[Message] = []

    def build_system_prompt(self, ontology_context: dict) -> str:
        """Assemble base template + skill.system_prompt + formatted ontology context."""
        skill_section = self.skill.system_prompt.strip() if self.skill.system_prompt else ""
        ontology_section = self._format_ontology(ontology_context)
        prompt = _BASE_TEMPLATE.format(
            skill_prompt=skill_section,
            ontology_context=ontology_section,
        ).strip()
        system_msg = Message(role="system", content=prompt)
        # Replace or prepend system message
        if self.messages and self.messages[0].role == "system":
            self.messages[0] = system_msg
        else:
            self.messages.insert(0, system_msg)
        return prompt

    def append_user_message(self, content: str) -> None:
        self.messages.append(Message(role="user", content=content))

    def append_assistant_message(
        self,
        content: str | None,
        tool_calls: list[ToolCall] | None,
    ) -> None:
        self.messages.append(Message(role="assistant", content=content, tool_calls=tool_calls))

    def append_tool_result(self, tool_call_id: str, result: str) -> None:
        self.messages.append(Message(role="tool", content=result, tool_call_id=tool_call_id))

    def get_messages_for_llm(self) -> list[Message]:
        return list(self.messages)

    @staticmethod
    def extract_structured(message: str) -> tuple[str, list[dict] | None]:
        """Extract ```structured ... ``` JSON blocks. Returns (cleaned_text, items_or_None)."""
        pattern = re.compile(r"```structured\s*\n(.*?)\n```", re.DOTALL)
        items: list[dict] = []
        for match in pattern.finditer(message):
            try:
                payload = json.loads(match.group(1))
            except (ValueError, TypeError):
                continue
            if isinstance(payload, list):
                items.extend(p for p in payload if isinstance(p, dict))
            elif isinstance(payload, dict):
                items.append(payload)
        cleaned = pattern.sub("", message).strip()
        return cleaned, items or None

    @staticmethod
    def _format_ontology(ontology_context: dict) -> str:
        """Format objects as: ### Name\ndescription\n- field: type (semantic_type)"""
        objects: list[dict[str, Any]] = ontology_context.get("objects", [])
        if not objects:
            return "无可用对象"
        lines: list[str] = []
        for obj in objects:
            name = obj.get("name", "Unknown")
            description = obj.get("description", "")
            lines.append(f"### {name}")
            if description:
                lines.append(description)
            for prop in obj.get("properties", []):
                prop_name = prop.get("name", "")
                prop_type = prop.get("type", "string")
                semantic_type = prop.get("semantic_type", "")
                if semantic_type:
                    lines.append(f"- {prop_name}: {prop_type} ({semantic_type})")
                else:
                    lines.append(f"- {prop_name}: {prop_type}")
            lines.append("")
        return "\n".join(lines).strip()
