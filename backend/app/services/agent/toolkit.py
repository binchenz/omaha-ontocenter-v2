from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.services.ontology.importer import OntologyImporter
from app.services.ontology.store import OntologyStore


def _summarize_dataframe(name: str, df) -> dict:
    """Convert a pandas DataFrame to the summary shape shared by scan_tables and infer_ontology."""
    return {
        "name": name,
        "row_count": int(len(df)),
        "columns": [{"name": str(c), "type": str(df[c].dtype)} for c in df.columns],
        "sample_values": {
            str(c): [str(v) for v in df[c].dropna().astype(str).head(20).tolist()]
            for c in df.columns
        },
    }


class AgentToolkit:
    def __init__(
        self,
        omaha_service,
        ontology_context: Dict = None,
        project_id: Optional[int] = None,
        session_id: Optional[int] = None,
        db: Optional[Session] = None,
    ):
        self.omaha_service = omaha_service
        self.ontology_context = ontology_context or {}
        self.project_id = project_id
        self.session_id = session_id
        self.db = db
        self._uploaded_tables: Dict = {}
        self._tools = {
            "query_data": self._query_data,
            "list_objects": self._list_objects,
            "get_schema": self._get_schema,
            "generate_chart": self._generate_chart,
            "upload_file": self._upload_file,
            "assess_quality": self._assess_quality,
            "clean_data": self._clean_data,
            "load_template": self._load_template,
            "scan_tables": self._scan_tables,
            "infer_ontology": self._infer_ontology,
            "confirm_ontology": self._confirm_ontology,
            "edit_ontology": self._edit_ontology,
        }

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "name": "query_data",
                "description": "Query data from a business object. Use this to retrieve records with optional filters and column selection.",
                "parameters": {
                    "object_type": {"type": "string", "description": "Name of the object to query", "required": True},
                    "columns": {"type": "array", "description": "Columns to return. Omit for all columns.", "required": False},
                    "filters": {"type": "array", "description": "Filter conditions: [{field, operator, value}]", "required": False},
                    "limit": {"type": "integer", "description": "Max rows to return (default 100)", "required": False},
                },
            },
            {
                "name": "list_objects",
                "description": "List all available business objects and their descriptions.",
                "parameters": {},
            },
            {
                "name": "get_schema",
                "description": "Get the schema (fields, types, semantic types) of a business object.",
                "parameters": {
                    "object_type": {"type": "string", "description": "Name of the object", "required": True},
                },
            },
            {
                "name": "generate_chart",
                "description": "Generate an ECharts chart config from query result data. Call this after query_data to visualize results.",
                "parameters": {
                    "data": {"type": "array", "description": "Array of data rows from query_data result", "required": True},
                    "chart_type": {"type": "string", "description": "Chart type: bar, line, pie, scatter", "required": True},
                    "title": {"type": "string", "description": "Chart title", "required": False},
                    "x_field": {"type": "string", "description": "Field name for X axis", "required": True},
                    "y_field": {"type": "string", "description": "Field name for Y axis / values", "required": True},
                },
            },
            {
                "name": "upload_file",
                "description": "用户上传了文件后调用此工具，解析 Excel/CSV 文件并存入平台。不要主动调用，等用户上传文件后系统会自动触发。",
                "parameters": {
                    "file_path": {"type": "string", "description": "上传文件的服务器路径", "required": True},
                    "table_name": {"type": "string", "description": "存储的表名", "required": True},
                },
            },
            {
                "name": "assess_quality",
                "description": "评估已上传数据的质量，返回质量评分和问题清单。在用户上传文件后自动调用。",
                "parameters": {},
            },
            {
                "name": "clean_data",
                "description": "对已上传的数据执行清洗操作。rules 可选值：duplicate_rows, strip_whitespace, standardize_dates",
                "parameters": {
                    "rules": {"type": "array", "description": "要执行的清洗规则列表", "required": True},
                },
            },
            {
                "name": "load_template",
                "description": "加载行业模板，返回该行业典型的业务对象定义。在用户告知行业后调用，结果可作为 infer_ontology 的先验。",
                "parameters": {
                    "industry": {"type": "string", "description": "行业代码：retail / manufacturing / trade / service", "required": True}
                }
            },
            {
                "name": "scan_tables",
                "description": "扫描已上传的数据表，返回每张表的列、行数和样本值。在准备建模前调用。",
                "parameters": {}
            },
            {
                "name": "infer_ontology",
                "description": "基于已上传数据 + 可选行业模板，调 LLM 推断本体（业务对象、字段语义、关系）。结果存为草稿，用户确认后才生效。如果已有草稿会被覆盖。",
                "parameters": {
                    "industry": {
                        "type": "string",
                        "description": "行业代码（可选）。如有值，会先加载对应模板作为 LLM 提示",
                        "required": False
                    }
                }
            },
            {
                "name": "confirm_ontology",
                "description": "用户确认建模草稿后调用。把草稿持久化到本体库，setup_stage 推到 ready。如无草稿则报错。",
                "parameters": {}
            },
            {
                "name": "edit_ontology",
                "description": "修改已确认的本体（重命名对象/字段、改语义类型、增删字段或关系）。setup_stage 必须为 ready 才能调用。",
                "parameters": {
                    "action": {
                        "type": "string",
                        "description": "rename_object | rename_property | change_semantic_type | update_description | add_property | remove_property | add_relationship | remove_relationship",
                        "required": True
                    },
                    "object_name": {"type": "string", "required": True},
                    "property_name": {"type": "string", "required": False},
                    "new_value": {"type": "string", "required": False},
                    "data_type": {"type": "string", "required": False},
                    "semantic_type": {"type": "string", "required": False},
                    "to_object": {"type": "string", "required": False},
                    "from_field": {"type": "string", "required": False},
                    "to_field": {"type": "string", "required": False},
                }
            },
        ]

    def execute_tool(self, tool_name: str, params: dict[str, Any]) -> dict:
        handler = self._tools.get(tool_name)
        if not handler:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        try:
            return handler(params)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _query_data(self, params: dict) -> dict:
        return self.omaha_service.query_objects(
            object_type=params["object_type"],
            selected_columns=params.get("columns"),
            filters=params.get("filters"),
            limit=params.get("limit", 100),
        )

    def _list_objects(self, params: dict) -> dict:
        return {"success": True, "objects": self.ontology_context.get("objects", [])}

    def _get_schema(self, params: dict) -> dict:
        obj_name = params["object_type"]
        for obj in self.ontology_context.get("objects", []):
            if obj["name"] == obj_name:
                return {"success": True, "schema": obj}
        return {"success": False, "error": f"Object '{obj_name}' not found"}

    def _generate_chart(self, params: dict) -> dict:
        data = params.get("data", [])
        chart_type = params.get("chart_type", "bar")
        title = params.get("title", "")
        x_field = params.get("x_field", "")
        y_field = params.get("y_field", "")

        if chart_type == "pie":
            chart_config = {
                "title": {"text": title},
                "tooltip": {"trigger": "item"},
                "series": [{
                    "type": "pie",
                    "data": [
                        {"name": str(row.get(x_field, "")), "value": row.get(y_field, 0)}
                        for row in data
                    ],
                }],
            }
        else:
            chart_config = {
                "title": {"text": title},
                "tooltip": {"trigger": "axis"},
                "xAxis": {"type": "category", "data": [str(row.get(x_field, "")) for row in data]},
                "yAxis": {"type": "value"},
                "series": [{"type": chart_type, "data": [row.get(y_field, 0) for row in data]}],
            }
        return {"success": True, "chart_config": chart_config}

    def _load_tables(self) -> Dict:
        if self.project_id is not None and self.session_id is not None:
            from app.services.data.uploaded_table_store import UploadedTableStore
            return UploadedTableStore.load_all(self.project_id, self.session_id)
        return self._uploaded_tables

    def _persist_tables(self, tables: Dict) -> None:
        if self.project_id is not None and self.session_id is not None:
            from app.services.data.uploaded_table_store import UploadedTableStore
            UploadedTableStore.replace_all(self.project_id, self.session_id, tables)
        else:
            self._uploaded_tables = tables

    def _upload_file(self, params: dict) -> dict:
        import pandas as pd
        file_path = params["file_path"]
        table_name = params["table_name"]
        try:
            if file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path)
            tables = self._load_tables()
            tables[table_name] = df
            self._persist_tables(tables)
            return {
                "success": True,
                "data": {
                    "table_name": table_name,
                    "row_count": len(df),
                    "column_count": len(df.columns),
                    "columns": [{"name": c, "type": str(df[c].dtype)} for c in df.columns],
                }
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _assess_quality(self, params: dict) -> dict:
        from app.services.data.cleaner import DataCleaner
        tables = self._load_tables()
        if not tables:
            return {"success": False, "error": "没有已上传的数据，请先上传文件"}
        report = DataCleaner.assess(tables)
        return {"success": True, "data": report.to_dict()}

    def _clean_data(self, params: dict) -> dict:
        from app.services.data.cleaner import DataCleaner
        tables = self._load_tables()
        if not tables:
            return {"success": False, "error": "没有已上传的数据"}
        rules = params.get("rules", [])
        cleaned = DataCleaner.clean(tables, auto_rules=rules)
        summary = {f"{name}_cleaned": len(df) for name, df in cleaned.items()}
        self._persist_tables(cleaned)
        return {"success": True, "data": summary}

    def _load_template(self, params: dict) -> dict:
        from app.services.ontology.template_loader import TemplateLoader
        industry = params.get("industry")
        if not industry:
            return {"success": False, "error": "industry 参数必填"}
        template = TemplateLoader.load(industry)
        if not template:
            return {"success": False, "error": f"未知行业模板: {industry}"}
        return {
            "success": True,
            "data": {
                "industry": template.get("industry", industry),
                "display_name": template.get("display_name", industry),
                "domain": template.get("domain", industry),
                "objects": template.get("objects", []),
                "relationships": template.get("relationships", []),
            }
        }

    def _scan_tables(self, params: dict) -> dict:
        tables = self._load_tables()
        if not tables:
            return {"success": False, "error": "没有已上传的数据，请先上传文件"}
        summaries = [_summarize_dataframe(name, df) for name, df in tables.items()]
        return {"success": True, "data": {"tables": summaries}}

    def _infer_ontology(self, params: dict) -> dict:
        from app.services.ontology.inferrer import (
            OntologyInferrer, compact_template, merge_template_semantic_types,
        )
        from app.services.ontology.draft_store import OntologyDraftStore
        from app.services.ontology.template_loader import TemplateLoader
        from app.services.ontology.schema_scanner import TableSummary

        if self.project_id is None or self.session_id is None:
            return {"success": False, "error": "project_id/session_id missing on toolkit"}

        tables = self._load_tables()
        if not tables:
            return {"success": False, "error": "没有已上传的数据，请先上传文件"}

        template = None
        template_hint = None
        industry = params.get("industry")
        if industry:
            template = TemplateLoader.load(industry)
            if template:
                template_hint = compact_template(template)

        inferrer = OntologyInferrer()
        inferred_objects = []
        warnings: list[str] = []
        for name, df in tables.items():
            summary_dict = _summarize_dataframe(name, df)
            summary = TableSummary(
                name=summary_dict["name"],
                row_count=summary_dict["row_count"],
                columns=[{**c, "nullable": True} for c in summary_dict["columns"]],
                sample_values=summary_dict["sample_values"],
            )
            try:
                obj = inferrer.infer_table(summary, datasource_id="upload", template_hint=template_hint)
            except Exception as e:
                warnings.append(f"{name}: 推断失败 ({e})")
                continue
            if obj is None:
                warnings.append(f"{name}: LLM 未返回有效结果")
                continue
            inferred_objects.append(obj)

        if template:
            inferred_objects = merge_template_semantic_types(inferred_objects, template)

        relationships = inferrer.infer_relationships_by_naming(inferred_objects)

        OntologyDraftStore.save(
            project_id=self.project_id,
            session_id=self.session_id,
            objects=[obj.model_dump() for obj in inferred_objects],
            relationships=[rel.model_dump() for rel in relationships],
            warnings=warnings,
        )

        if not inferred_objects:
            return {
                "success": False,
                "error": "LLM 未能从已上传数据推断出业务对象。" + ("; ".join(warnings) if warnings else ""),
                "data": {"warnings": warnings},
            }

        return {
            "success": True,
            "data": {
                "objects_count": len(inferred_objects),
                "relationships_count": len(relationships),
                "warnings": warnings,
                "objects": [obj.model_dump() for obj in inferred_objects],
                "relationships": [rel.model_dump() for rel in relationships],
                "template_name": template.get("display_name") if template else None,
            }
        }

    def _confirm_ontology(self, params: dict) -> dict:
        from app.services.ontology.draft_store import OntologyDraftStore
        from app.models.project import Project

        if self.project_id is None or self.session_id is None:
            return {"success": False, "error": "project_id/session_id missing on toolkit"}
        if self.db is None:
            return {"success": False, "error": "db session missing on toolkit"}

        draft = OntologyDraftStore.load(self.project_id, self.session_id)
        if not draft or not draft.get("objects"):
            return {"success": False, "error": "没有可确认的草稿，请先调用 infer_ontology"}

        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        if not project:
            return {"success": False, "error": f"project {self.project_id} not found"}

        tenant_id = project.tenant_id or project.owner_id

        config = {
            "datasources": [{"id": "upload", "type": "csv"}],
            "ontology": {
                "objects": [
                    {
                        "name": obj["name"],
                        "datasource": obj.get("datasource_id", "upload"),
                        "source_entity": obj.get("source_entity", obj["name"]),
                        "description": obj.get("description"),
                        "business_context": obj.get("business_context"),
                        "domain": obj.get("domain"),
                        "properties": [
                            {
                                "name": p["name"],
                                "type": p.get("data_type", "string"),
                                "semantic_type": p.get("semantic_type"),
                                "description": p.get("description"),
                            }
                            for p in obj.get("properties", [])
                        ],
                    }
                    for obj in draft["objects"]
                ],
            },
        }

        importer = OntologyImporter(self.db)
        result = importer.import_dict(tenant_id, config)

        project.setup_stage = "ready"
        self.db.commit()

        OntologyDraftStore.clear(self.project_id, self.session_id)

        return {
            "success": True,
            "data": {
                "objects_created": result.get("objects_created", 0),
                "objects_updated": result.get("objects_updated", 0),
                "relationships_created": result.get("relationships_created", 0),
            }
        }

    def _edit_ontology(self, params: dict) -> dict:
        from app.models.project import Project
        from sqlalchemy.exc import SQLAlchemyError

        if self.project_id is None or self.db is None:
            return {"success": False, "error": "project_id/db missing on toolkit"}

        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        if not project:
            return {"success": False, "error": f"project {self.project_id} not found"}
        if project.setup_stage != "ready":
            return {"success": False, "error": "edit_ontology 仅在已确认本体后可用 (setup_stage=ready)"}

        action = params.get("action")
        object_name = params.get("object_name")
        if not action or not object_name:
            return {"success": False, "error": "action 和 object_name 必填"}

        # Per-action required-key validation up front so missing keys produce
        # a clear error instead of being swallowed by the broad except below.
        required_by_action = {
            "rename_object": ("new_value",),
            "rename_property": ("property_name", "new_value"),
            "change_semantic_type": ("property_name", "new_value"),
            "update_description": ("new_value",),
            "add_property": ("property_name",),
            "remove_property": ("property_name",),
            "add_relationship": ("to_object", "from_field", "to_field"),
            "remove_relationship": (),
        }
        if action not in required_by_action:
            return {"success": False, "error": f"未知 action: {action}"}
        missing = [k for k in required_by_action[action] if not params.get(k)]
        if missing:
            return {"success": False, "error": f"缺少参数: {', '.join(missing)}"}

        tenant_id = project.tenant_id or project.owner_id
        store = OntologyStore(self.db)

        obj = store.get_object(tenant_id, object_name)
        if obj is None:
            return {"success": False, "error": f"未找到对象: {object_name}"}

        try:
            if action == "rename_object":
                ok = store.rename_object(tenant_id, object_name, params["new_value"])
            elif action == "rename_property":
                ok = store.rename_property(obj.id, params["property_name"], params["new_value"])
            elif action == "change_semantic_type":
                ok = store.update_property_semantic_type(obj.id, params["property_name"], params["new_value"])
            elif action == "update_description":
                if params.get("property_name"):
                    ok = store.update_property_description(obj.id, params["property_name"], params["new_value"])
                else:
                    ok = store.update_object_description(tenant_id, object_name, params["new_value"])
            elif action == "add_property":
                store.add_property(
                    object_id=obj.id,
                    name=params["property_name"],
                    data_type=params.get("data_type", "string"),
                    semantic_type=params.get("semantic_type"),
                )
                ok = True
            elif action == "remove_property":
                ok = store.remove_property(obj.id, params["property_name"])
            elif action == "add_relationship":
                to_obj = store.get_object(tenant_id, params["to_object"])
                if not to_obj:
                    return {"success": False, "error": f"未找到目标对象: {params['to_object']}"}
                store.add_relationship(
                    tenant_id=tenant_id,
                    name=f"{object_name}_{params['to_object']}",
                    from_object_id=obj.id,
                    to_object_id=to_obj.id,
                    relationship_type=params.get("relationship_type", "belongs_to"),
                    from_field=params["from_field"],
                    to_field=params["to_field"],
                )
                ok = True
            else:  # remove_relationship
                ok = store.remove_relationship(tenant_id, params.get("new_value") or object_name)

            if not ok:
                return {"success": False, "error": f"操作失败: {action}"}

            self.db.commit()
            return {"success": True, "data": {"action": action, "object_name": object_name}}

        except SQLAlchemyError as e:
            self.db.rollback()
            return {"success": False, "error": f"数据库错误: {e}"}
