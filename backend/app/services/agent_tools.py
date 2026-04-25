from typing import Any, Dict


class AgentToolkit:
    def __init__(self, omaha_service, ontology_context: Dict = None):
        self.omaha_service = omaha_service
        self.ontology_context = ontology_context or {}
        self._uploaded_tables: Dict = {}
        self._tools = {
            "query_data": self._query_data,
            "list_objects": self._list_objects,
            "get_schema": self._get_schema,
            "generate_chart": self._generate_chart,
            "upload_file": self._upload_file,
            "assess_quality": self._assess_quality,
            "clean_data": self._clean_data,
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

    def _upload_file(self, params: dict) -> dict:
        import pandas as pd
        file_path = params["file_path"]
        table_name = params["table_name"]
        try:
            if file_path.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file_path)
            else:
                df = pd.read_csv(file_path)
            self._uploaded_tables[table_name] = df
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
        from app.services.data_cleaner import DataCleaner
        if not self._uploaded_tables:
            return {"success": False, "error": "没有已上传的数据，请先上传文件"}
        report = DataCleaner.assess(self._uploaded_tables)
        return {"success": True, "data": report.to_dict()}

    def _clean_data(self, params: dict) -> dict:
        from app.services.data_cleaner import DataCleaner
        if not self._uploaded_tables:
            return {"success": False, "error": "没有已上传的数据"}
        rules = params.get("rules", [])
        cleaned = DataCleaner.clean(self._uploaded_tables, auto_rules=rules)
        summary = {f"{name}_cleaned": len(df) for name, df in cleaned.items()}
        self._uploaded_tables = cleaned
        return {"success": True, "data": summary}
