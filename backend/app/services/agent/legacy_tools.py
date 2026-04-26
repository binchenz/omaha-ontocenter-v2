from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.services.ontology_store import OntologyStore
from app.services.omaha import OmahaService


def get_tools(db: Session) -> List[Dict[str, Any]]:
    return [
        {
            "name": "query_ontology_object",
            "description": "Query a single ontology object with optional filters and column selection.",
            "parameters": {
                "object_name": {"type": "string", "description": "Name of the ontology object"},
                "columns": {"type": "array", "items": {"type": "string"}, "description": "Columns to select"},
                "filters": {"type": "array", "description": "List of filter dicts with field, operator, value"},
            },
        },
        {
            "name": "aggregate_ontology_object",
            "description": "Run an aggregation (SUM, AVG, COUNT, MIN, MAX) on an ontology object property.",
            "parameters": {
                "object_name": {"type": "string"},
                "property": {"type": "string", "description": "Property to aggregate"},
                "aggregation": {"type": "string", "enum": ["SUM", "AVG", "COUNT", "MIN", "MAX"]},
                "filters": {"type": "array"},
            },
        },
        {
            "name": "get_ontology_schema",
            "description": "Get the schema (columns, types, semantic types) of an ontology object.",
            "parameters": {
                "object_name": {"type": "string"},
            },
        },
        {
            "name": "get_object_health_status",
            "description": "Get health status for an ontology object based on its health rules.",
            "parameters": {
                "object_name": {"type": "string"},
            },
        },
    ]


def execute_tool(
    tool_name: str,
    params: dict,
    db: Session,
    tenant_id: int,
    config_yaml: str = None,
) -> Dict[str, Any]:
    store = OntologyStore(db)

    if tool_name == "query_ontology_object":
        obj_name = params.get("object_name")
        if not config_yaml:
            obj = store.get_object(tenant_id, obj_name)
            if not obj:
                return {"success": False, "error": f"Object '{obj_name}' not found"}
            # Simulate a simple query result using stored metadata
            return {
                "success": True,
                "data": [{"_placeholder": f"Query result for {obj_name}"}],
                "count": 1,
            }
        service = OmahaService(config_yaml)
        return service.query_objects(
            object_type=obj_name,
            selected_columns=params.get("columns"),
            filters=params.get("filters"),
        )

    if tool_name == "aggregate_ontology_object":
        obj_name = params.get("object_name")
        prop_name = params.get("property")
        agg = params.get("aggregation", "SUM")
        obj = store.get_object(tenant_id, obj_name)
        if not obj:
            return {"success": False, "error": f"Object '{obj_name}' not found"}
        prop = next((p for p in obj.properties if p.name == prop_name), None)
        if not prop:
            return {"success": False, "error": f"Property '{prop_name}' not found"}
        return {
            "success": True,
            "aggregation": agg,
            "property": prop_name,
            "value": None,
            "message": f"{agg}({prop_name}) aggregation placeholder - requires real datasource",
        }

    if tool_name == "get_ontology_schema":
        obj_name = params.get("object_name")
        if not config_yaml:
            obj = store.get_object(tenant_id, obj_name)
            if not obj:
                return {"success": False, "error": f"Object '{obj_name}' not found"}
            return {
                "success": True,
                "name": obj.name,
                "source_entity": obj.source_entity,
                "fields": [
                    {"name": p.name, "type": p.data_type, "semantic_type": p.semantic_type}
                    for p in obj.properties
                ],
            }
        service = OmahaService(config_yaml)
        return service.get_object_schema(object_type=obj_name)

    if tool_name == "get_object_health_status":
        obj_name = params.get("object_name")
        obj = store.get_object(tenant_id, obj_name)
        if not obj:
            return {"success": False, "error": f"Object '{obj_name}' not found"}
        return {
            "success": True,
            "object": obj.name,
            "health_rules": [
                {"metric": r.metric, "expression": r.expression,
                 "warning": r.warning_threshold, "critical": r.critical_threshold}
                for r in obj.health_rules
            ],
        }

    return {"success": False, "error": f"Unknown tool: {tool_name}"}
