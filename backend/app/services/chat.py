"""
Chat service with LLM function calling.
"""
from typing import List, Dict, Any, Optional
import json
import os
from sqlalchemy.orm import Session

from app.models.chat_session import ChatSession, ChatMessage
from app.services.omaha import omaha_service
from app.services.chart_engine import ChartEngine


class ChatService:
    """Service for handling chat interactions with LLM."""

    SYSTEM_TEMPLATE = """你是一个数据分析助手，可以帮助用户查询和分析数据。

可用的数据对象：
{ontology}

你可以使用以下工具来访问数据：
- list_objects: 列出所有可用的对象类型
- get_schema: 获取对象的字段定义
- get_relationships: 获取对象间的关系
- query_data: 执行数据查询
- save_asset: 保存查询为资产
- list_assets: 列出已保存的资产
- get_lineage: 获取资产的数据血缘

请用中文回答用户的问题。"""

    def __init__(self, project_id: int, db: Session):
        self.project_id = project_id
        self.db = db
        self.chart_engine = ChartEngine()

    def _build_ontology_context(self, config_yaml: str) -> str:
        """Build ontology context string from project config."""
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

        This is a placeholder that will be completed in Task 6.
        """
        # Load history
        history = self._load_history(session_id, limit=20)

        # Build system prompt
        ontology_ctx = self._build_ontology_context(config_yaml)
        system_prompt = self.SYSTEM_TEMPLATE.format(ontology=ontology_ctx)

        # Get tool schemas
        tools = self._get_tool_schemas()

        # TODO: Implement LLM calling logic in Task 6
        # For now, return a placeholder response
        response_text = "这是一个占位响应。LLM 集成将在 Task 6 中完成。"

        # Save messages
        self._save_messages(session_id, user_message, response_text)

        return {
            "message": response_text,
            "data_table": None,
            "chart_config": None,
            "sql": None
        }
