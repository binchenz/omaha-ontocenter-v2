"""
Chat service with LLM function calling.
"""
from typing import List, Dict, Any, Optional
import json
import os
from decimal import Decimal
from pathlib import Path
from sqlalchemy.orm import Session

# Load .env from project root (two levels up from this file)
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent.parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass

try:
    import openai
except ImportError:
    openai = None

try:
    import anthropic
except ImportError:
    anthropic = None

from app.models.chat_session import ChatSession, ChatMessage
from app.services.omaha import omaha_service
from app.services.semantic import semantic_service
from app.services.chart_engine import ChartEngine


def _json_dumps(obj: Any) -> str:
    """JSON serialize with Decimal support."""
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(obj, ensure_ascii=False, default=default)


class ChatService:
    """Service for handling chat interactions with LLM."""

    SYSTEM_TEMPLATE = """你是一个数据分析助手，帮助运营人员查询和分析拼便宜平台的商品数据。

可用的数据对象：
{ontology}

重要提示：
1. 查询时必须使用 "ObjectName.field_name" 格式，例如 "Product.sku_name"
2. 竞品平台信息请使用 GoodsMallMapping 对象（包含 platform_name, goods_name, similarity 等字段）
3. 多平台价格对比请使用 PriceAnalysis 对象（包含 ppy_price, jdws_price, yjp_price, xsj_price）
4. gross_margin 是计算字段，可以直接查询，无需手动计算
5. 如果查询失败，请尝试使用 get_schema 工具先了解字段名称

你可以使用以下工具：
- list_objects: 列出所有可用的对象类型
- get_schema: 获取对象的字段定义（不确定字段名时先调用此工具）
- get_relationships: 获取对象间的关系
- query_data: 执行数据查询
- save_asset: 保存查询为资产

请用中文回答用户的问题，回答要简洁清晰。"""

    def __init__(self, project_id: int, db: Session):
        self.project_id = project_id
        self.db = db
        self.chart_engine = ChartEngine()

    def _build_ontology_context(self, config_yaml: str) -> str:
        """Build ontology context string from project config, enriched with semantic metadata."""
        semantic_result = semantic_service.parse_config(config_yaml)

        if semantic_result.get("valid") and semantic_result.get("objects"):
            context_lines = []
            for obj_name, obj_meta in semantic_result["objects"].items():
                agent_ctx = semantic_service.build_agent_context(obj_meta)
                context_lines.append(f"### {obj_name}\n{agent_ctx}")

            metrics = semantic_result.get("metrics", [])
            if metrics:
                context_lines.append("### 业务指标")
                for m in metrics:
                    context_lines.append(f"  - {m.get('name')} ({m.get('label', '')}): {m.get('description', '')} = {m.get('formula', '')}")

            return "\n\n".join(context_lines)

        # Fallback to basic ontology context
        result = omaha_service.build_ontology(config_yaml)
        if not result.get("valid"):
            return "无可用对象"

        objects = result.get("ontology", {}).get("objects", [])
        context_lines = []
        for obj in objects:
            name = obj.get("name", "Unknown")
            properties = obj.get("properties", [])
            prop_names = [p.get("name") for p in properties if p.get("name")]
            context_lines.append(f"- {name}: {', '.join(prop_names)}")

        return "\n".join(context_lines)

    def _load_history(self, session_id: int, limit: int = 20) -> List[Dict[str, str]]:
        """Load recent chat history."""
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )

        # Reverse to chronological order
        messages = list(reversed(messages))

        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.content
            })

        return history

    def _get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get MCP tool schemas in LLM function calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_objects",
                    "description": "列出项目中所有可用的 Ontology 对象类型",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_schema",
                    "description": "获取指定对象类型的字段定义",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "object_type": {
                                "type": "string",
                                "description": "对象类型名称"
                            }
                        },
                        "required": ["object_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_relationships",
                    "description": "获取指定对象类型的关系定义",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "object_type": {
                                "type": "string",
                                "description": "对象类型名称"
                            }
                        },
                        "required": ["object_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_data",
                    "description": "执行数据查询，支持列选择、过滤和 JOIN",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "object_type": {
                                "type": "string",
                                "description": "基础对象类型"
                            },
                            "selected_columns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要查询的列名列表"
                            },
                            "filters": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "过滤条件列表"
                            },
                            "joins": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "JOIN 配置列表"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回行数限制",
                                "default": 100
                            }
                        },
                        "required": ["object_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_asset",
                    "description": "保存查询配置为可重用的资产",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "资产名称"
                            },
                            "description": {
                                "type": "string",
                                "description": "资产描述"
                            },
                            "base_object": {
                                "type": "string",
                                "description": "基础对象类型"
                            },
                            "selected_columns": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "filters": {
                                "type": "array",
                                "items": {"type": "object"}
                            },
                            "joins": {
                                "type": "array",
                                "items": {"type": "object"}
                            },
                            "row_count": {
                                "type": "integer"
                            }
                        },
                        "required": ["name", "base_object"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_assets",
                    "description": "列出已保存的资产",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_lineage",
                    "description": "获取资产的数据血缘信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "asset_id": {
                                "type": "integer",
                                "description": "资产 ID"
                            }
                        },
                        "required": ["asset_id"]
                    }
                }
            }
        ]

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any], config_yaml: str) -> Dict[str, Any]:
        """Execute a single MCP tool call."""
        try:
            if tool_name == "list_objects":
                result = omaha_service.build_ontology(config_yaml)
                if result.get("valid"):
                    objects = result.get("ontology", {}).get("objects", [])
                    return {"objects": [obj.get("name") for obj in objects]}
                return {"error": "Invalid ontology"}

            elif tool_name == "get_schema":
                object_type = tool_args.get("object_type")
                result = omaha_service.get_object_schema(config_yaml, object_type)
                return result

            elif tool_name == "get_relationships":
                object_type = tool_args.get("object_type")
                result = omaha_service.get_relationships(config_yaml, object_type)
                return {"relationships": result}

            elif tool_name == "query_data":
                result = omaha_service.query_objects(
                    config_yaml,
                    tool_args.get("object_type"),
                    tool_args.get("selected_columns"),
                    tool_args.get("filters"),
                    tool_args.get("joins"),
                    tool_args.get("limit", 100)
                )
                return result

            elif tool_name == "save_asset":
                # This would call the assets API internally
                return {"message": "Asset saved (not implemented in this service)"}

            elif tool_name == "list_assets":
                # This would call the assets API internally
                return {"assets": []}

            elif tool_name == "get_lineage":
                # This would call the assets API internally
                return {"lineage": []}

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"error": str(e)}

    def _save_messages(
        self,
        session_id: int,
        user_message: str,
        assistant_message: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        chart_config: Optional[Dict[str, Any]] = None
    ):
        """Save user and assistant messages to database."""
        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_message
        )
        self.db.add(user_msg)

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=assistant_message,
            tool_calls=json.dumps(tool_calls) if tool_calls else None,
            chart_config=json.dumps(chart_config) if chart_config else None
        )
        self.db.add(assistant_msg)
        self.db.commit()

    def send_message(
        self,
        session_id: int,
        user_message: str,
        config_yaml: str,
        llm_provider: str = "deepseek"
    ) -> Dict[str, Any]:
        """
        Send a message and get response with optional chart.

        Supports OpenAI, Anthropic (Claude), and DeepSeek.
        """
        # Load history
        history = self._load_history(session_id, limit=20)

        # Build system prompt
        ontology_ctx = self._build_ontology_context(config_yaml)
        system_prompt = self.SYSTEM_TEMPLATE.format(ontology=ontology_ctx)

        # Get tool schemas
        tools = self._get_tool_schemas()

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        # Call LLM with function calling
        try:
            if llm_provider == "openai":
                response_text, data_table, chart_config, sql = self._call_openai(
                    messages, tools, config_yaml
                )
            elif llm_provider == "anthropic":
                response_text, data_table, chart_config, sql = self._call_anthropic(
                    messages, tools, config_yaml
                )
            elif llm_provider == "deepseek":
                response_text, data_table, chart_config, sql = self._call_deepseek(
                    messages, tools, config_yaml
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {llm_provider}")

        except Exception as e:
            response_text = f"抱歉，处理您的请求时出错：{str(e)}"
            data_table = None
            chart_config = None
            sql = None

        # Save messages
        self._save_messages(session_id, user_message, response_text, chart_config=chart_config)

        return {
            "message": response_text,
            "data_table": data_table,
            "chart_config": chart_config,
            "sql": sql
        }

    def _call_openai_compatible(
        self,
        client,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        config_yaml: str
    ) -> tuple:
        """Shared function calling loop for OpenAI-compatible APIs (OpenAI + DeepSeek)."""
        max_iterations = 10
        data_table = None
        chart_config = None
        sql = None

        for _ in range(max_iterations):
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice="auto"
            )

            message = response.choices[0].message

            if not message.tool_calls:
                return message.content, data_table, chart_config, sql

            messages.append({
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    }
                    for tc in message.tool_calls
                ]
            })

            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                try:
                    tool_args = json.loads(tool_call.function.arguments)
                except json.JSONDecodeError:
                    tool_args = {}
                result = self._execute_tool(tool_name, tool_args, config_yaml)

                if tool_name == "query_data" and result.get("data"):
                    data_table = result["data"]
                    sql = result.get("sql")
                    try:
                        chart_type = self.chart_engine.select_chart_type(data_table)
                        if chart_type:
                            chart_config = self.chart_engine.build_chart_config(data_table, chart_type)
                    except Exception:
                        pass  # chart generation is optional

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": _json_dumps(result)
                })

        return "抱歉，处理超时。", data_table, chart_config, sql

    def _call_openai(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        config_yaml: str
    ) -> tuple:
        """Call OpenAI API with function calling."""
        if not openai:
            raise ImportError("openai package not installed")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        client = openai.OpenAI(api_key=api_key)
        return self._call_openai_compatible(client, "gpt-4-turbo-preview", messages, tools, config_yaml)

    def _call_anthropic(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        config_yaml: str
    ) -> tuple:
        """Call Anthropic Claude API with function calling."""
        if not anthropic:
            raise ImportError("anthropic package not installed")

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        client = anthropic.Anthropic(api_key=api_key)

        # Convert tools to Claude format
        claude_tools = [
            {
                "name": t["function"]["name"],
                "description": t["function"]["description"],
                "input_schema": t["function"]["parameters"]
            }
            for t in tools
        ]

        # Extract system message
        system_msg = messages[0]["content"] if messages[0]["role"] == "system" else ""
        claude_messages = [m for m in messages if m["role"] != "system"]

        # Function calling loop
        max_iterations = 10
        data_table = None
        chart_config = None
        sql = None

        for _ in range(max_iterations):
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                system=system_msg,
                messages=claude_messages,
                tools=claude_tools
            )

            # Check for tool use
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # No more tool calls, extract text
                text_blocks = [b.text for b in response.content if hasattr(b, 'text')]
                return " ".join(text_blocks), data_table, chart_config, sql

            # Execute tool calls
            claude_messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for tool_use in tool_use_blocks:
                result = self._execute_tool(tool_use.name, tool_use.input, config_yaml)

                # Extract data for chart generation
                if tool_use.name == "query_data" and "data" in result:
                    data_table = result["data"]
                    sql = result.get("sql")

                    # Generate chart
                    chart_type = self.chart_engine.select_chart_type(data_table)
                    if chart_type:
                        chart_config = self.chart_engine.build_chart_config(data_table, chart_type)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": _json_dumps(result)
                })

            claude_messages.append({
                "role": "user",
                "content": tool_results
            })

        return "抱歉，处理超时。", data_table, chart_config, sql

    def _call_deepseek(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        config_yaml: str
    ) -> tuple:
        """Call DeepSeek API with function calling (OpenAI-compatible)."""
        if not openai:
            raise ImportError("openai package not installed")
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY not set")
        client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        return self._call_openai_compatible(client, "deepseek-chat", messages, tools, config_yaml)
