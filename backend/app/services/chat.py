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
from app.models.project import Project
from app.services.omaha import OmahaService
from app.services.semantic import semantic_service
from app.services.chart_engine import ChartEngine
from app.services.ontology_store import OntologyStore
from app.services.agent import format_onboarding_context


def _json_dumps(obj: Any) -> str:
    """JSON serialize with Decimal support."""
    def default(o):
        if isinstance(o, Decimal):
            return float(o)
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    return json.dumps(obj, ensure_ascii=False, default=default)


class ChatService:
    """Service for handling chat interactions with LLM."""

    SYSTEM_TEMPLATE = """你是一个企业数据分析助手，帮助用户接入数据、整理语义、回答业务问题。
你的目标用户是中小企业的非技术人员，请始终用业务语言回答，避免技术术语（"表"、"字段"、"SQL"等用"对象"、"属性"、"查询"代替）。

## 可用数据对象
{ontology}

## 工作方式（ReAct）
你必须遵循 思考→行动→观察→回答 的循环：
1. **思考**：分析用户意图，判断当前应该接入数据、清洗数据、确认建模、还是查询数据
2. **行动**：调用合适的工具（见下方工具列表）
3. **观察**：分析工具返回结果
4. **回答**：用业务语言给出简洁结论

## 强制规则
- 任何涉及具体数据的问题，必须先调用工具查询，不得凭空回答
- 查询时 filters 中的 field 不需要加对象前缀，直接用字段名
- selected_columns 中可加对象前缀（如 "订单.金额"）
- **查询一次后立即基于结果回答，不要反复查询**
- 如果查询结果为空或不符合预期，直接告知用户，不要编造数据
- 用户上传文件后，自动调用 assess_quality 评估数据质量并展示结果
- **建模请求必须走工具链，不能用文字描述代替**：用户说"整理成业务对象"、"帮我建模"、"梳理数据"、"识别对象"等意图时，必须按顺序调用 load_template（如已知行业）→ scan_tables → infer_ontology。文字描述对象/字段不算建模。
- **infer_ontology 成功后必须返回 ontology_preview 结构化块**，不允许只用 Markdown 表格代替（用户需要点击"确认建模"按钮）。
- **用户说"确认建模"或"我确认"或"OK"且当前阶段是 modeling 时**，立即调用 confirm_ontology 工具，不要再让用户重复一遍。

## 结构化富组件输出

当你需要让用户从几个选项里选择，或展示结构化报告时，可以在回复中嵌入 ```structured ... ``` 代码块（JSON 格式），前端会渲染成卡片。

**给用户提供选项时（如选择行业）：**
```structured
{{"type": "options", "content": "你们公司是做什么行业的？", "options": [{{"label": "零售/电商", "value": "retail"}}, {{"label": "制造业", "value": "manufacturing"}}, {{"label": "贸易", "value": "trade"}}, {{"label": "餐饮/服务", "value": "service"}}]}}
```

**展示数据质量报告时（assess_quality 工具返回后）：**
```structured
{{"type": "panel", "panel_type": "quality_report", "content": "数据质量报告", "data": {{"score": 67, "issues": [...]}}}}
```

**展示建模草稿（infer_ontology 工具返回后，必须用此格式展示）：**
```structured
{{"type": "panel", "panel_type": "ontology_preview", "content": "我识别出这些业务对象，请确认", "data": {{"template_name": "零售/电商", "objects": [...], "relationships": [...], "warnings": [...]}}}}
```
注意：`data` 字段直接复制 infer_ontology 工具返回的 data 内容。

注意：
- `data` 直接复制 assess_quality 工具返回的 data 内容
- structured 块外可以有自然语言文字解释，但选项/面板本身用块包裹
- 不要在 structured 块里重复同样的选项文字（避免冗余）

## 工作流工具（按使用阶段）

**接入阶段**
- upload_file: 用户上传文件后系统自动触发（不要主动调用）
- list_datasources: 列出已接入的数据源

**清洗阶段**
- assess_quality: 评估数据质量，返回评分和问题清单
- clean_data: 执行清洗（rules: duplicate_rows / strip_whitespace / standardize_dates）

**建模阶段**
- load_template: 加载行业模板（用户告知行业后调用）
- scan_tables: 扫描已上传数据
- infer_ontology: LLM 推断业务对象 + 字段语义 + 关系（结果写草稿，可传 industry 参数复用模板）
- confirm_ontology: 持久化草稿到本体库
- edit_ontology: 修改已确认的本体（仅 setup_stage=ready 时可用）

**查询阶段**
- list_objects: 列出所有业务对象
- get_schema: 获取对象的字段定义
- query_data: 查询业务数据
- generate_chart: 生成图表

请用中文回答，基于真实数据，简洁清晰。"""

    def __init__(self, project_id: int, db: Session):
        self.project_id = project_id
        self.db = db
        self.chart_engine = ChartEngine()
        # 预加载项目信息和本体
        project = self.db.query(Project).filter(Project.id == project_id).first()
        self.project = project
        self.tenant_id = project.tenant_id or project.owner_id if project else None
        self.omaha_service = None

    def _get_ontology_context(self) -> dict:
        """Get ontology from database store."""
        if not self.tenant_id:
            return {}
        store = OntologyStore(self.db)
        return store.get_full_ontology(self.tenant_id)

    def _build_ontology_context(self, config_yaml: str) -> str:
        """Build ontology context string from database store, fallback to config yaml."""
        # 首先尝试从数据库获取
        ontology = self._get_ontology_context()
        objects = ontology.get("objects", [])
        
        if objects:
            context_lines = []
            for obj in objects:
                name = obj.get("name", "Unknown")
                description = obj.get("description", "")
                context_lines.append(f"### {name}")
                if description:
                    context_lines.append(f"{description}")
                properties = obj.get("properties", [])
                prop_lines = []
                for prop in properties:
                    prop_name = prop.get("name", "")
                    prop_type = prop.get("type", "string")
                    semantic_type = prop.get("semantic_type", "")
                    if semantic_type:
                        prop_lines.append(f"- {prop_name}: {prop_type} ({semantic_type})")
                    else:
                        prop_lines.append(f"- {prop_name}: {prop_type}")
                context_lines.extend(prop_lines)
                context_lines.append("")
            return "\n".join(context_lines)

        # Fallback to original implementation with config yaml
        try:
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
        except Exception:
            pass

        # Fallback to basic ontology context
        try:
            omaha_service = OmahaService(config_yaml)
            result = omaha_service.build_ontology()
            if result.get("valid"):
                objects = result.get("ontology", {}).get("objects", [])
                context_lines = []
                for obj in objects:
                    name = obj.get("name", "Unknown")
                    properties = obj.get("properties", [])
                    prop_names = [p.get("name") for p in properties if p.get("name")]
                    context_lines.append(f"- {name}: {', '.join(prop_names)}")

                return "\n".join(context_lines)
        except Exception:
            pass

        return "无可用对象"

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
                    "description": "执行数据查询，支持列选择、过滤和 JOIN。重要：统计分析时必须使用聚合函数（SUM/AVG/COUNT），不要查询明细数据",
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
                    "name": "screen_stocks",
                    "description": "跨股票筛选工具。先获取股票列表，再批量查询财务/估值数据，最后按条件过滤。适用于'找出ROE>15%的股票'、'股息率最高的10只银行股'等场景",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "stock_filters": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "股票基本信息过滤条件，如按行业筛选 [{\"field\": \"industry\", \"operator\": \"=\", \"value\": \"银行\"}]"
                            },
                            "metric_object": {
                                "type": "string",
                                "description": "要查询的指标对象，如 FinancialIndicator、ValuationMetric"
                            },
                            "metric_columns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要查询的指标字段，如 [\"roe\", \"debt_to_assets\"]"
                            },
                            "metric_filters": {
                                "type": "array",
                                "items": {"type": "object"},
                                "description": "指标过滤条件，如 [{\"field\": \"roe\", \"operator\": \">=\", \"value\": 15}]"
                            },
                            "sort_by": {
                                "type": "string",
                                "description": "排序字段，如 \"roe\""
                            },
                            "sort_order": {
                                "type": "string",
                                "description": "排序方向：desc（降序）或 asc（升序）",
                                "default": "desc"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "返回结果数量限制",
                                "default": 10
                            }
                        },
                        "required": ["metric_object", "metric_columns"]
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
            },
            {
                "type": "function",
                "function": {
                    "name": "assess_quality",
                    "description": "评估当前会话已上传数据的质量。返回质量评分（0-100）和问题清单（重复行、缺失值、格式不一致等）。用户上传文件后应自动调用此工具。",
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
                    "name": "clean_data",
                    "description": "对当前会话已上传的数据执行清洗。rules 必填，可选值：duplicate_rows（去重）、strip_whitespace（去空格）、standardize_dates（统一日期格式）",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "rules": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要执行的清洗规则列表"
                            }
                        },
                        "required": ["rules"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "load_template",
                    "description": "加载行业模板，返回该行业典型的业务对象定义。在用户告知行业后调用，结果可作为 infer_ontology 的先验。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "industry": {"type": "string", "description": "行业代码：retail / manufacturing / trade / service"}
                        },
                        "required": ["industry"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "scan_tables",
                    "description": "扫描已上传的数据表，返回每张表的列、行数和样本值。在准备建模前调用。",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "infer_ontology",
                    "description": "基于已上传数据 + 可选行业模板，调 LLM 推断本体。结果存为草稿，用户确认后才生效。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "industry": {"type": "string", "description": "行业代码（可选）"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "confirm_ontology",
                    "description": "用户确认建模草稿后调用。把草稿持久化到本体库，setup_stage 推到 ready。",
                    "parameters": {"type": "object", "properties": {}, "required": []}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_ontology",
                    "description": "修改已确认的本体。setup_stage 必须为 ready 才能调用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "description": "rename_object|rename_property|change_semantic_type|update_description|add_property|remove_property|add_relationship|remove_relationship"},
                            "object_name": {"type": "string"},
                            "property_name": {"type": "string"},
                            "new_value": {"type": "string"},
                            "data_type": {"type": "string"},
                            "semantic_type": {"type": "string"},
                            "to_object": {"type": "string"},
                            "from_field": {"type": "string"},
                            "to_field": {"type": "string"}
                        },
                        "required": ["action", "object_name"]
                    }
                }
            }
        ]

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any], config_yaml: str) -> Dict[str, Any]:
        """Execute a single MCP tool call."""
        try:
            if tool_name == "list_objects":
                # 优先从数据库获取
                ontology = self._get_ontology_context()
                objects = ontology.get("objects", [])
                if objects:
                    return {"objects": [obj.get("name") for obj in objects]}
                # Fallback
                omaha_service = OmahaService(config_yaml)
                result = omaha_service.build_ontology()
                if result.get("valid"):
                    objects = result.get("ontology", {}).get("objects", [])
                    return {"objects": [obj.get("name") for obj in objects]}
                return {"error": "Invalid ontology"}

            elif tool_name == "get_schema":
                object_type = tool_args.get("object_type")
                # 优先从数据库获取
                ontology = self._get_ontology_context()
                for obj in ontology.get("objects", []):
                    if obj.get("name") == object_type:
                        return {"success": True, "schema": obj}
                # Fallback
                omaha_service = OmahaService(config_yaml)
                return omaha_service.get_object_schema(object_type)

            elif tool_name == "get_relationships":
                object_type = tool_args.get("object_type")
                # 优先从数据库获取
                ontology = self._get_ontology_context()
                relationships = ontology.get("relationships", [])
                obj_rels = []
                for rel in relationships:
                    if rel.get("from") == object_type or rel.get("to") == object_type:
                        obj_rels.append(rel)
                if obj_rels:
                    return {"relationships": obj_rels}
                # Fallback
                omaha_service = OmahaService(config_yaml)
                return {"relationships": omaha_service.get_relationships(object_type)}

            elif tool_name == "query_data":
                # 使用配置文件查询数据
                if not self.omaha_service:
                    self.omaha_service = OmahaService(config_yaml)
                result = self.omaha_service.query_objects(
                    tool_args.get("object_type"),
                    tool_args.get("selected_columns"),
                    tool_args.get("filters"),
                    tool_args.get("joins"),
                    min(tool_args.get("limit", 10), 20)  # Cap at 20 rows to avoid LLM timeout
                )
                # Truncate data sent to LLM to avoid context overflow
                if result.get("data") and len(result["data"]) > 10:
                    result = dict(result)
                    result["data"] = result["data"][:10]
                    result["note"] = f"数据已截断，仅显示前10条（共{result.get('count', '?')}条）"
                return result

            elif tool_name == "screen_stocks":
                return self._screen_stocks(tool_args, config_yaml)

            elif tool_name == "save_asset":
                # This would call the assets API internally
                return {"message": "Asset saved (not implemented in this service)"}

            elif tool_name == "list_assets":
                # This would call the assets API internally
                return {"assets": []}

            elif tool_name == "get_lineage":
                # This would call the assets API internally
                return {"lineage": []}

            elif tool_name in (
                "assess_quality", "clean_data",
                "load_template", "scan_tables",
                "infer_ontology", "confirm_ontology", "edit_ontology",
            ):
                from app.services.agent_tools import AgentToolkit
                toolkit = AgentToolkit(
                    omaha_service=None,
                    project_id=self.project_id,
                    session_id=getattr(self, "_current_session_id", None),
                    db=self.db,
                )
                result = toolkit.execute_tool(tool_name, tool_args)
                if result.get("success"):
                    self._advance_setup_stage_for_tool(tool_name)
                return result

            else:
                return {"error": f"Unknown tool: {tool_name}"}

        except Exception as e:
            return {"error": str(e)}

    def _advance_setup_stage_for_tool(self, tool_name: str) -> None:
        """Advance project.setup_stage based on tool that just succeeded."""
        if not self.project:
            return
        transitions = {
            "clean_data": ("cleaning", "modeling"),
            # confirm_ontology already sets setup_stage=ready inside the toolkit
        }
        pair = transitions.get(tool_name)
        if not pair:
            return
        expected, next_stage = pair
        if self.project.setup_stage == expected:
            self.project.setup_stage = next_stage
            self.db.commit()

    def _screen_stocks(self, args: Dict[str, Any], config_yaml: str) -> Dict[str, Any]:
        """Screen stocks with multi-object filtering (financial + valuation + technical)."""
        try:
            if not self.omaha_service:
                self.omaha_service = OmahaService(config_yaml)
                
            stock_filters = args.get("stock_filters", [])
            metric_objects = args.get("metric_objects", [])  # NEW: support multiple objects
            sort_by = args.get("sort_by")
            sort_order = args.get("sort_order", "desc")
            limit = min(args.get("limit", 10), 20)

            # Backward compatibility: support old single-object format
            if not metric_objects and args.get("metric_object"):
                metric_objects = [{
                    "object": args.get("metric_object"),
                    "columns": args.get("metric_columns", []),
                    "filters": args.get("metric_filters", [])
                }]

            if not metric_objects:
                return {"error": "metric_objects is required"}

            # Step 1: Get stock list (max 200)
            stock_result = self.omaha_service.query_objects(
                "Stock",
                selected_columns=["Stock.ts_code", "Stock.name", "Stock.industry"],
                filters=stock_filters,
                limit=200
            )
            if not stock_result.get("success"):
                return {"error": f"获取股票列表失败: {stock_result.get('error')}"}

            stocks = stock_result.get("data", [])
            if not stocks:
                return {"data": [], "count": 0, "message": "没有找到符合条件的股票"}

            # Step 2: Batch query all metric objects for each stock
            results = []
            for stock in stocks:
                ts_code = stock.get("ts_code")
                row = {"ts_code": ts_code, "name": stock.get("name"), "industry": stock.get("industry")}

                # Query each metric object and merge results
                for metric_obj in metric_objects:
                    obj_name = metric_obj.get("object")
                    columns = metric_obj.get("columns", [])
                    cols = [f"{obj_name}.{c}" for c in columns]

                    r = self.omaha_service.query_objects(
                        obj_name,
                        selected_columns=cols,
                        filters=[{"field": "ts_code", "operator": "=", "value": ts_code}],
                        limit=1
                    )
                    if r.get("success") and r.get("data"):
                        row.update(r["data"][0])

                # Only include stocks that have data from all metric objects
                if len(row) > 3:  # More than just ts_code, name, industry
                    results.append(row)

            # Step 3: Apply all metric filters client-side
            for metric_obj in metric_objects:
                for f in metric_obj.get("filters", []):
                    field = f.get("field")
                    op = f.get("operator", ">=")
                    val = f.get("value")
                    filtered = []
                    for row in results:
                        v = row.get(field)
                        if v is None:
                            continue
                        try:
                            v = float(v)
                            val_f = float(val)
                            if op in (">=", "=>") and v >= val_f:
                                filtered.append(row)
                            elif op == ">" and v > val_f:
                                filtered.append(row)
                            elif op in ("<=", "=<") and v <= val_f:
                                filtered.append(row)
                            elif op == "<" and v < val_f:
                                filtered.append(row)
                            elif op == "=" and v == val_f:
                                filtered.append(row)
                        except (TypeError, ValueError):
                            pass
                    results = filtered

            # Step 4: Sort
            if sort_by and results:
                results.sort(
                    key=lambda x: float(x.get(sort_by, 0) or 0),
                    reverse=(sort_order == "desc")
                )

            # Step 5: Limit
            results = results[:limit]

            return {
                "success": True,
                "data": results,
                "count": len(results),
                "total_screened": len(stocks)
            }

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
        self._current_session_id = session_id
        # Load history
        history = self._load_history(session_id, limit=20)

        # Build system prompt
        ontology_ctx = self._build_ontology_context(config_yaml)
        setup_stage = getattr(self.project, "setup_stage", None) or "idle"
        onboarding_ctx = format_onboarding_context(setup_stage)
        base_prompt = self.SYSTEM_TEMPLATE.format(ontology=ontology_ctx)
        system_prompt = f"{onboarding_ctx}\n\n{base_prompt}" if onboarding_ctx else base_prompt

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

        clean_message, structured = self._extract_structured(response_text)

        return {
            "message": clean_message,
            "data_table": data_table,
            "chart_config": chart_config,
            "sql": sql,
            "setup_stage": setup_stage,
            "structured": structured,
        }

    @staticmethod
    def _extract_structured(message: str) -> tuple[str, list[dict] | None]:
        """Extract ```structured ...``` JSON blocks from the message.

        Returns (cleaned_message, structured_items or None).
        """
        import re

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

    def _call_openai_compatible(
        self,
        client,
        model: str,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]],
        config_yaml: str
    ) -> tuple:
        """ReAct loop for OpenAI-compatible APIs (OpenAI + DeepSeek).

        First turn: force tool use (tool_choice='required') so Agent always
        queries real data before answering. Subsequent turns: auto.
        """
        max_iterations = 8  # Increased to handle complex aggregation queries
        data_table = None
        chart_config = None
        sql = None
        first_turn = True
        force_answer = False  # After successful query, force text answer

        for iteration in range(max_iterations):
            # First turn: force tool call; after successful query: force answer
            if force_answer:
                tool_choice = "none"
            elif first_turn:
                tool_choice = "required"
            else:
                tool_choice = "auto"
            first_turn = False

            response = client.chat.completions.create(
                model=model,
                messages=messages,
                tools=tools,
                tool_choice=tool_choice
            )

            message = response.choices[0].message

            # No tool calls → final answer
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

                # If query failed, add helpful hint so Agent can self-correct
                if tool_name == "query_data" and not result.get("success"):
                    result["hint"] = (
                        "查询失败。请检查：1) object_type 必须大写开头（如 Product）"
                        "2) selected_columns 格式为 ObjectName.field_name"
                        "3) 先调用 get_schema 确认字段名"
                    )

                if tool_name == "query_data" and result.get("data"):
                    data_table = result["data"]
                    sql = result.get("sql")
                    force_answer = True  # Force text answer after successful query
                    try:
                        chart_type = self.chart_engine.select_chart_type(data_table)
                        if chart_type:
                            chart_config = self.chart_engine.build_chart_config(data_table, chart_type)
                    except Exception:
                        pass

                tool_content = _json_dumps(result)
                # After a successful query_data, nudge Agent to answer now
                if tool_name == "query_data" and result.get("success") and result.get("data"):
                    tool_content += "\n\n请基于以上数据直接回答用户问题，不要再查询更多数据。"
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_content
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
