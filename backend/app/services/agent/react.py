import json
from typing import Any, Literal

from app.config import settings
from app.schemas.chat.agent import AgentChatResponse, ToolCallRecord

try:
    import openai
except ImportError:
    openai = None


SetupStage = Literal["idle", "connecting", "cleaning", "modeling", "ready"]
SETUP_STAGES: tuple[SetupStage, ...] = ("idle", "connecting", "cleaning", "modeling", "ready")


ONBOARDING_PROMPTS: dict[SetupStage, str] = {
    "idle": """## 当前状态：新用户引导
用户刚创建项目，还没有接入数据。你的任务是引导用户完成数据接入。
1. 先问用户是什么行业的
2. 再问用什么方式管理数据（Excel/数据库/SaaS软件）
3. 引导用户上传文件或填写连接信息
用业务语言，不要用技术术语。""",

    "connecting": """## 当前状态：数据接入中
用户正在接入数据源。如果上传了文件，自动调用 assess_quality 评估数据质量。""",

    "cleaning": """## 当前状态：数据清洗中
数据已接入，正在清洗。展示质量问题，引导用户确认清洗方案。""",

    "modeling": """## 当前状态：语义建模中
数据已清洗，正在构建本体。引导用户确认业务对象和字段含义。""",

    "ready": "",
}


def format_onboarding_context(setup_stage: str | None) -> str:
    """Return onboarding guidance for the given stage. Empty for ready/unknown."""
    if not setup_stage:
        return ""
    return ONBOARDING_PROMPTS.get(setup_stage, "")

SYSTEM_PROMPT_TEMPLATE = """你是一个企业数据分析助手。你可以帮助用户查询和分析业务数据。

{onboarding_context}

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
    def __init__(
        self,
        ontology_context: dict,
        toolkit,
        tenant_knowledge: list[str] = None,
        provider: str = None,
    ):
        self.ontology_context = ontology_context
        self.toolkit = toolkit
        self.tenant_knowledge = tenant_knowledge or []
        self.provider = provider
        self._client = None
        self._model = None

    def build_system_prompt(self, setup_stage: str = "ready") -> str:
        objects_ctx = self._format_objects()
        health_ctx = self._format_health_rules()
        goals_ctx = self._format_goals()
        knowledge_ctx = self._format_knowledge()
        tools_ctx = self._format_tools()

        onboarding_ctx = self._format_onboarding(setup_stage)

        return SYSTEM_PROMPT_TEMPLATE.format(
            objects_context=objects_ctx,
            health_rules_context=health_ctx,
            goals_context=goals_ctx,
            knowledge_context=knowledge_ctx,
            tools_context=tools_ctx,
            onboarding_context=onboarding_ctx,
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

    def _format_onboarding(self, setup_stage: str) -> str:
        return format_onboarding_context(setup_stage)

    def format_tool_result(self, tool_name: str, result: dict) -> str:
        if not result.get("success"):
            return f"工具调用失败: {result.get('error', '未知错误')}"
        if "data" in result:
            data = result["data"]
            count = result.get("count", len(data))
            try:
                preview = json.dumps(data[:5], ensure_ascii=False, indent=2)
            except TypeError:
                preview = str(data[:5])
            return f"查询返回 {count} 条记录:\n{preview}"
        try:
            return json.dumps(result, ensure_ascii=False, indent=2)
        except TypeError:
            return str(result)

    @staticmethod
    def parse_tool_call(tool_call: dict) -> tuple[str, dict]:
        name = tool_call["name"]
        args = tool_call.get("arguments", "{}")
        if isinstance(args, str):
            args = json.loads(args)
        return name, args

    def chat(self, message: str, history: list[dict] = None) -> AgentChatResponse:
        system_prompt = self.build_system_prompt()
        tools_schema = self._build_tools_schema()

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages += history
        messages.append({"role": "user", "content": message})

        return self._react_loop(messages, tools_schema)

    def _react_loop(
        self, messages: list[dict], tools_schema: list[dict], max_iterations: int = 8
    ) -> AgentChatResponse:
        tool_calls_log: list[ToolCallRecord] = []
        data_table = None
        chart_config = None
        sql = None
        first_turn = True
        force_answer = False

        for _ in range(max_iterations):
            if force_answer:
                tool_choice = "none"
            elif first_turn:
                tool_choice = "required"
            else:
                tool_choice = "auto"
            first_turn = False

            response = self._call_llm(messages, tools_schema, tool_choice)
            message_obj = response.choices[0].message

            if not message_obj.tool_calls:
                return AgentChatResponse(
                    response=message_obj.content or "",
                    tool_calls=tool_calls_log,
                    data_table=data_table,
                    chart_config=chart_config,
                    sql=sql,
                )

            messages.append({
                "role": "assistant",
                "content": message_obj.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in message_obj.tool_calls
                ],
            })

            for tc in message_obj.tool_calls:
                name = tc.function.name
                try:
                    params = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    params = {}

                result = self.toolkit.execute_tool(name, params)

                if name == "query_data" and result.get("success") and result.get("data"):
                    data_table = result["data"]
                    sql = result.get("sql")
                    force_answer = True
                if name == "generate_chart" and result.get("success") and result.get("chart_config"):
                    chart_config = result["chart_config"]

                tool_content = self.format_tool_result(name, result)
                if name == "query_data" and result.get("success") and result.get("data"):
                    tool_content += "\n\n请基于以上数据直接回答用户问题。"

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_content,
                })

                summary = tool_content[:500] + "..." if len(tool_content) > 500 else tool_content
                tool_calls_log.append(ToolCallRecord(
                    tool_name=name, params=params, result_summary=summary,
                ))

        return AgentChatResponse(
            response="分析完成，但达到了最大迭代次数。",
            tool_calls=tool_calls_log,
            data_table=data_table,
            chart_config=chart_config,
            sql=sql,
        )

    def _call_llm(
        self, messages: list[dict], tools: list[dict] | None = None, tool_choice: str = "auto"
    ):
        if openai is None:
            raise ImportError("openai package not installed")

        if self._client is None:
            provider = self.provider or self._detect_provider()
            if provider == "deepseek":
                self._client = openai.OpenAI(
                    api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_BASE_URL
                )
                self._model = settings.DEEPSEEK_MODEL
            elif provider == "openai":
                self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
                self._model = "gpt-4o-mini"
            else:
                raise ValueError(f"Unsupported provider: {provider}")

        kwargs: dict[str, Any] = {"model": self._model, "messages": messages}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        return self._client.chat.completions.create(**kwargs)

    def _build_tools_schema(self) -> list[dict]:
        schema = []
        for tool in self.toolkit.get_tool_definitions():
            properties: dict[str, Any] = {}
            required: list[str] = []
            for pname, pdef in tool.get("parameters", {}).items():
                param_schema: dict[str, Any] = {
                    "type": pdef.get("type", "string"),
                    "description": pdef.get("description", ""),
                }
                if param_schema["type"] == "array":
                    param_schema["items"] = {"type": "string"}
                properties[pname] = param_schema
                if pdef.get("required"):
                    required.append(pname)
            schema.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            })
        return schema

    def _detect_provider(self) -> str:
        if settings.DEEPSEEK_API_KEY:
            return "deepseek"
        if settings.OPENAI_API_KEY:
            return "openai"
        raise ValueError("No LLM provider configured. Set DEEPSEEK_API_KEY or OPENAI_API_KEY.")
