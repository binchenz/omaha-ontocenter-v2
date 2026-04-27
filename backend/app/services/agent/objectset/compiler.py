"""Compiler for ObjectSet to OmahaService query arguments."""

from typing import Any, Dict, List, Optional
from app.services.agent.objectset import ObjectSet


# Operator mapping from ObjectSet operators to SQL operators
OPERATOR_MAP = {
    "eq": "=",
    "ne": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
    "contains": "LIKE",
    "in": "IN",
}


def compile_query_args(object_set: ObjectSet) -> Dict[str, Any]:
    """
    Compile ObjectSet into dict shape OmahaService.query_objects expects.

    Returns:
        Dict with keys: object_type, selected_columns, filters, limit
    """
    # Compile filters
    compiled_filters = []
    for filter_obj in object_set.filters:
        compiled_filters.append({
            "field": filter_obj.field,
            "operator": OPERATOR_MAP.get(filter_obj.operator, filter_obj.operator),
            "value": filter_obj.value,
        })

    # Compile selected columns (None if empty)
    selected_columns = list(object_set.selected) if object_set.selected else None

    return {
        "object_type": object_set.object_type,
        "selected_columns": selected_columns,
        "filters": compiled_filters,
        "limit": object_set.limit,
    }
