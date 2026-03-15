"""
SemanticQueryBuilder — builds SQL queries with full semantic layer awareness.

Resolves property names to column names, expands computed properties to SQL
expressions, and builds complete SELECT/JOIN/WHERE/LIMIT SQL.
"""
from typing import Any, Dict, List, Optional, Tuple
import re

from app.services.semantic import semantic_service


class SemanticQueryBuilder:
    """Builds SQL queries with semantic layer awareness."""

    def __init__(self, config_yaml: str, object_type: str):
        """
        Parse both ontology and semantic config for the given object type.

        Args:
            config_yaml: Full YAML config string
            object_type: Name of the ontology object (e.g. "Product")
        """
        import yaml
        config = yaml.safe_load(config_yaml)
        ontology = config.get("ontology", {})

        # Find object definition
        objects = ontology.get("objects", [])
        self.obj_def = next((o for o in objects if o.get("name") == object_type), None)
        if not self.obj_def:
            raise ValueError(f"Object type '{object_type}' not found in ontology")

        self.object_type = object_type
        self.table_name = self.obj_def.get("table", object_type)
        self.relationships = ontology.get("relationships", [])
        self.all_objects = objects
        self.db_type = None  # set later

        # Parse semantic layer
        semantic_result = semantic_service.parse_config(config_yaml)
        if semantic_result.get("valid") and object_type in semantic_result.get("objects", {}):
            obj_meta = semantic_result["objects"][object_type]
            self.property_map = obj_meta.get("property_map", {})  # prop_name -> col_name
            self.computed_properties = obj_meta.get("computed_properties", {})
        else:
            # Fallback: build property_map from obj_def properties
            self.property_map = {}
            self.computed_properties = {}
            for prop in self.obj_def.get("properties", []):
                name = prop.get("name")
                col = prop.get("column", name)
                if name:
                    self.property_map[name] = col

    def resolve_column(self, col_ref: str) -> str:
        """
        Resolve a column reference to a SQL expression.

        Handles:
        - "ObjectType.property_name" -> resolves property_name
        - "property_name" -> resolves directly
        - Computed properties -> expands formula to SQL expression AS alias

        Returns SQL expression string.
        """
        # Strip object type prefix if present
        if "." in col_ref:
            parts = col_ref.split(".", 1)
            prop_name = parts[1]
        else:
            prop_name = col_ref

        # Check if it's a computed property
        if prop_name in self.computed_properties:
            formula = self.computed_properties[prop_name].get("formula", "")
            try:
                sql_expr = semantic_service.expand_formula(formula, self.property_map)
                return f"({sql_expr}) AS {prop_name}"
            except ValueError:
                return prop_name

        # Regular property: map to column name
        if prop_name in self.property_map:
            col_name = self.property_map[prop_name]
            return f"{self.object_type}.{col_name}"

        # Unknown property: return as-is (let DB handle the error)
        return col_ref

    def resolve_filter_field(self, field: str) -> str:
        """Resolve a filter field name to a column reference."""
        # Strip object type prefix
        if "." in field:
            parts = field.split(".", 1)
            prop_name = parts[1]
        else:
            prop_name = field

        # Computed properties in filters become subexpressions
        if prop_name in self.computed_properties:
            formula = self.computed_properties[prop_name].get("formula", "")
            try:
                return f"({semantic_service.expand_formula(formula, self.property_map)})"
            except ValueError:
                return field

        # Regular property
        if prop_name in self.property_map:
            return f"{self.object_type}.{self.property_map[prop_name]}"

        return field

    def build(
        self,
        selected_columns: Optional[List[str]],
        filters: Optional[List[Dict[str, Any]]],
        joins: Optional[List[Dict[str, Any]]],
        limit: int,
        db_type: str,
    ) -> Tuple[str, List[Any]]:
        """
        Build a complete SQL query.

        Returns:
            Tuple of (sql_string, params_list)
        """
        self.db_type = db_type
        placeholder = "?" if db_type == "sqlite" else "%s"

        # Build SELECT clause
        if selected_columns:
            resolved = [self.resolve_column(col) for col in selected_columns]
            columns_str = ", ".join(resolved)
        else:
            # Select all base columns (exclude computed)
            if self.property_map:
                cols = [f"{self.object_type}.{col} AS {prop}"
                        for prop, col in self.property_map.items()]
                columns_str = ", ".join(cols)
            else:
                columns_str = "*"

        query = f"SELECT {columns_str} FROM {self.table_name} AS {self.object_type}"
        params: List[Any] = []

        # Build JOIN clause
        if joins:
            join_sql = self._build_join_clause(joins)
            if join_sql:
                query += f" {join_sql}"

        # Build WHERE clause
        if filters:
            where_parts = []
            for f in filters:
                field = self.resolve_filter_field(f.get("field", ""))
                operator = f.get("operator", "=")
                value = f.get("value")

                op_upper = operator.upper()
                if op_upper == "IN":
                    values = [v.strip() for v in str(value).split(",")]
                    placeholders = ",".join([placeholder] * len(values))
                    where_parts.append(f"{field} IN ({placeholders})")
                    params.extend(values)
                elif op_upper == "LIKE":
                    where_parts.append(f"{field} LIKE {placeholder}")
                    params.append(f"%{value}%")
                else:
                    where_parts.append(f"{field} {operator} {placeholder}")
                    params.append(value)

            if where_parts:
                query += f" WHERE {' AND '.join(where_parts)}"

        query += f" LIMIT {limit}"
        return query, params

    def _build_join_clause(self, joins: List[Dict[str, Any]]) -> str:
        """Build JOIN clause from join configs."""
        join_clauses = []
        for join in joins:
            rel_name = join.get("relationship_name")
            join_type = join.get("join_type", "LEFT")

            rel = next((r for r in self.relationships if r.get("name") == rel_name), None)
            if not rel:
                continue

            from_obj = rel.get("from_object")
            to_obj = rel.get("to_object")
            join_cond = rel.get("join_condition", {})
            from_field = join_cond.get("from_field")
            to_field = join_cond.get("to_field")

            # Find table names
            to_obj_def = next((o for o in self.all_objects if o.get("name") == to_obj), None)

            if not to_obj_def:
                continue

            to_table = to_obj_def.get("table", to_obj)
            join_clauses.append(
                f"{join_type} JOIN {to_table} AS {to_obj}"
                f" ON {from_obj}.{from_field} = {to_obj}.{to_field}"
            )

        return " ".join(join_clauses)
