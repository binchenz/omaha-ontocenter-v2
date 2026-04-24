import json
from typing import Any


SYSTEM_PROMPT_TEMPLATE = """你是一个企业数据分析助手。你可以帮助用户查询和分析业务数据。

## 可用的业务对象

{objects_context}

## 业务健康规则

{health_rules_context}

## 业务目标

{goals_context}

## 行业知识

{knowledge_context}

## 可用工具

{tools_context}

## 工作方式

1. 理解用户的意图
2. 选择合适的工具查询数据
3. 分析结果，用业务语言回答
4. 如果数据触发了健康规则的阈值，主动提醒
5. 不确定时说"我不确定"，不编造数据
6. 回答时说明数据来源和查询条件，保持透明"""


class AgentService:
    def __init__(self, ontology_context: dict, toolkit, tenant_knowledge: list[str] = None):
        self.ontology_context = ontology_context
        self.toolkit = toolkit
        self.tenant_knowledge = tenant_knowledge or []

    def build_system_prompt(self) -> str:
        objects_ctx = self._format_objects()
        health_ctx = self._format_health_rules()
        goals_ctx = self._format_goals()
        knowledge_ctx = self._format_knowledge()
        tools_ctx = self._format_tools()

        return SYSTEM_PROMPT_TEMPLATE.format(
            objects_context=objects_ctx,
            health_rules_context=health_ctx,
            goals_context=goals_ctx,
            knowledge_context=knowledge_ctx,
            tools_context=tools_ctx,
        )

    def _format_objects(self) -> str:
        lines = []
        for obj in self.ontology_context.get("objects", []):
            lines.append(f"### {obj['name']}")
            if obj.get("description"):
                lines.append(f"{obj['description']}")
            for prop in obj.get("properties", []):
                st = f" ({prop['semantic_type']})" if prop.get("semantic_type") else ""
                lines.append(f"- {prop['name']}: {prop.get('type', 'string')}{st}")
            lines.append("")
        return "\n".join(lines)

    def _format_health_rules(self) -> str:
        lines = []
        for obj in self.ontology_context.get("objects", []):
            for rule in obj.get("health_rules", []):
                lines.append(
                    f"- {obj['name']}.{rule['metric']}: "
                    f"warning={rule.get('warning', 'N/A')}, "
                    f"critical={rule.get('critical', 'N/A')}"
                )
                if rule.get("advice"):
                    lines.append(f"  建议: {rule['advice']}")
        return "\n".join(lines) if lines else "暂无健康规则"

    def _format_goals(self) -> str:
        lines = []
        for obj in self.ontology_context.get("objects", []):
            for goal in obj.get("goals", []):
                lines.append(f"- {goal['name']}: {goal['metric']} 目标 {goal['target']}")
        return "\n".join(lines) if lines else "暂无业务目标"

    def _format_knowledge(self) -> str:
        lines = []
        for obj in self.ontology_context.get("objects", []):
            for k in obj.get("knowledge", []):
                lines.append(f"- {k}")
        for k in self.tenant_knowledge:
            lines.append(f"- {k}")
        return "\n".join(lines) if lines else "暂无行业知识"

    def _format_tools(self) -> str:
        lines = []
        for tool in self.toolkit.get_tool_definitions():
            lines.append(f"### {tool['name']}")
            lines.append(f"{tool['description']}")
            if tool.get("parameters"):
                for pname, pdef in tool["parameters"].items():
                    req = " (必填)" if pdef.get("required") else ""
                    lines.append(f"- {pname}: {pdef.get('description', '')}{req}")
            lines.append("")
        return "\n".join(lines)

    def format_tool_result(self, tool_name: str, result: dict) -> str:
        if not result.get("success"):
            return f"工具调用失败: {result.get('error', '未知错误')}"
        if "data" in result:
            data = result["data"]
            count = result.get("count", len(data))
            preview = json.dumps(data[:5], ensure_ascii=False, indent=2)
            return f"查询返回 {count} 条记录:\n{preview}"
        return json.dumps(result, ensure_ascii=False, indent=2)

    @staticmethod
    def parse_tool_call(tool_call: dict) -> tuple[str, dict]:
        name = tool_call["name"]
        args = tool_call.get("arguments", "{}")
        if isinstance(args, str):
            args = json.loads(args)
        return name, args
