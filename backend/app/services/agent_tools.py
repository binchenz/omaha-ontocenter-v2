from typing import Any


class AgentToolkit:
    def __init__(self, omaha_service):
        self.omaha_service = omaha_service
        self._tools = {
            "query_data": self._query_data,
            "list_objects": self._list_objects,
            "get_schema": self._get_schema,
        }

    def get_tool_definitions(self) -> list[dict]:
        return [
            {
                "name": "query_data",
                "description": "Query data from a business object. Use this to retrieve records with optional filters and column selection.",
                "parameters": {
                    "object_type": {"type": "string", "description": "Name of the object to query (e.g. Order, Customer, Product)", "required": True},
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
        ontology = self.omaha_service.build_ontology()
        return {"success": True, "objects": ontology.get("objects", [])}

    def _get_schema(self, params: dict) -> dict:
        schema = self.omaha_service.get_object_schema(params["object_type"])
        if schema:
            return {"success": True, "schema": schema}
        return {"success": False, "error": f"Object '{params['object_type']}' not found"}
