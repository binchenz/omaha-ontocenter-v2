"""
SemanticQueryBuilder — builds SQL queries with full semantic layer awareness.

Resolves property names to column names, expands computed properties to SQL
expressions, and builds complete SELECT/JOIN/WHERE/LIMIT SQL.
"""
from typing import Any, Dict, List, Optional, Tuple
import re

import yaml

from app.services.semantic.service import semantic_service


class SemanticQueryBuilder:
    """Builds SQL queries with semantic layer awareness."""

    def __init__(self, config_yaml: str, object_type: str):
        """
        Parse both ontology and semantic config for the given object type.

        Args:
            config_yaml: Full YAML config string
            object_type: Name of the ontology object (e.g. "Product")
        """
        config = yaml.safe_load(config_yaml)
        ontology = config.get("ontology", {})

        # Find object definition
        objects = ontology.get("objects", [])
        self.obj_def = next((o for o in objects if o.get("name") == object_type), None)
        if not self.obj_def:
            raise ValueError(f"Object type '{object_type}' not found in ontology")

        self.object_type = object_type
        # Support both 'table' and 'query' fields
        self.table_name = self.obj_def.get("table")
        self.custom_query = self.obj_def.get("query")
        if not self.table_name and not self.custom_query:
            raise ValueError(f"Object '{object_type}' must have either 'table' or 'query' field")
        # Use object_type as table alias for custom queries
        if not self.table_name:
            self.table_name = object_type
        self.relationships = ontology.get("relationships", [])
        self.all_objects = objects
        self.db_type = None  # set later
        # Read default_filters from object definition
        self.default_filters = self.obj_def.get("default_filters", [])

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

    def _detect_needed_joins(self, selected_columns: List[str]) -> set:
        """
        Analyze selected_columns to identify objects that need to be JOINed.

        Args:
            selected_columns: List of column references like ["ProductPrice.sku_id", "Product.sku_name"]

        Returns:
            Set of object names that need to be JOINed, e.g. {"Product"}
        """
        needed_objects = set()

        for col in selected_columns:
            if "." in col:
                # Extract object name from "ObjectName.property_name"
                obj_name = col.split(".")[0]
                # If object name is not the current object, we need to JOIN
                if obj_name != self.object_type:
                    needed_objects.add(obj_name)

        return needed_objects

    def _find_relationship(self, target_object: str) -> Optional[Dict[str, Any]]:
        """
        Find a relationship from current object to target object.

        Args:
            target_object: Target object name

        Returns:
            Relationship definition dict, or None if not found
        """
        # Find relationship from current object to target object
        for rel in self.relationships:
            if (rel.get("from_object") == self.object_type and
                rel.get("to_object") == target_object):
                return rel

        # Find reverse relationship (from target to current)
        for rel in self.relationships:
            if (rel.get("from_object") == target_object and
                rel.get("to_object") == self.object_type):
                # Return reversed relationship
                return {
                    "name": rel.get("name"),
                    "from_object": self.object_type,
                    "to_object": target_object,
                    "type": "many_to_one" if rel.get("type") == "one_to_many" else "one_to_many",
                    "join_condition": {
                        "from_field": rel["join_condition"]["to_field"],
                        "to_field": rel["join_condition"]["from_field"]
                    }
                }

        return None

    def _build_auto_join_clause(self, relationship: Dict[str, Any]) -> str:
        """
        Build JOIN clause from relationship definition.

        Args:
            relationship: Relationship definition

        Returns:
            JOIN clause string
        """
        to_object = relationship.get("to_object")
        join_condition = relationship.get("join_condition", {})
        from_field = join_condition.get("from_field")
        to_field = join_condition.get("to_field")

        # Find target object definition
        to_obj_def = next((o for o in self.all_objects if o.get("name") == to_object), None)
        if not to_obj_def:
            return ""

        # Support both 'table' and 'query' fields
        if to_obj_def.get("table"):
            to_table = to_obj_def["table"]
        elif to_obj_def.get("query"):
            # If custom query, wrap as subquery
            to_table = f"({to_obj_def['query'].strip()})"
        else:
            return ""

        # Default to LEFT JOIN
        join_type = "LEFT JOIN"

        # Build join condition
        join_conditions = [f"{self.object_type}.{from_field} = {to_object}.{to_field}"]

        # Add additional conditions if present
        additional_conditions = relationship.get("additional_conditions", [])
        for cond in additional_conditions:
            from_f = cond.get("from_field")
            to_f = cond.get("to_field")
            if from_f and to_f:
                join_conditions.append(f"{self.object_type}.{from_f} = {to_object}.{to_f}")

        join_on = " AND ".join(join_conditions)

        return f"{join_type} {to_table} AS {to_object} ON {join_on}"

    def resolve_column(self, col_ref: str) -> str:
        """
        Resolve a column reference to a SQL expression.

        Handles:
        - "ObjectType.property_name" -> resolves property_name
        - "property_name" -> resolves directly
        - Computed properties -> expands formula to SQL expression AS alias
        - Aggregate functions like "AVG(Product.gross_margin) as avg_margin"
          -> expands computed properties inside the function

        Returns SQL expression string.
        """
        # Handle aggregate functions: AVG(...), SUM(...), COUNT(...), etc.
        agg_match = re.match(r'^(\w+)\((.+?)\)(\s+as\s+\w+)?$', col_ref.strip(), re.IGNORECASE)
        if agg_match:
            func_name = agg_match.group(1)
            inner = agg_match.group(2).strip()
            alias = agg_match.group(3) or ""
            # Resolve the inner expression (without AS alias for computed fields)
            resolved_inner = self._resolve_inner(inner)
            return f"{func_name}({resolved_inner}){alias}"

        return self._resolve_simple_col(col_ref)

    def _resolve_inner(self, col_ref: str) -> str:
        """Resolve column inside aggregate function - no AS alias for computed fields."""
        if "." in col_ref:
            parts = col_ref.split(".", 1)
            prop_name = parts[1]
        else:
            prop_name = col_ref

        if prop_name in self.computed_properties:
            formula = self.computed_properties[prop_name].get("formula", "")
            try:
                sql_expr = semantic_service.expand_formula(formula, self.property_map)
                return f"({sql_expr})"  # No AS alias inside aggregate
            except ValueError:
                return prop_name

        if prop_name in self.property_map:
            return f"{self.object_type}.{self.property_map[prop_name]}"

        return col_ref

    def _resolve_simple_col(self, col_ref: str) -> str:
        """Resolve a simple column reference (no aggregate functions)."""
        # Strip object type prefix if present
        if "." in col_ref:
            parts = col_ref.split(".", 1)
            obj_name = parts[0]
            prop_name = parts[1]

            # If referencing another object, return as-is (will be handled by JOIN)
            if obj_name != self.object_type:
                return col_ref
        else:
            prop_name = col_ref

        # Check if it's a computed property
        if prop_name in self.computed_properties:
            formula = self.computed_properties[prop_name].get("formula", "")
            try:
                sql_expr = semantic_service.expand_formula(formula, self.property_map)
                # When used standalone (not inside aggregate), add AS alias
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

    def _apply_single_filter(
        self,
        f: Dict[str, Any],
        placeholder: str,
        where_parts: List[str],
        params: List[Any],
    ) -> None:
        """Apply a single filter to the WHERE clause parts and params."""
        field = self.resolve_filter_field(f.get("field", ""))
        operator = f.get("operator", "=")
        value = f.get("value")

        op_upper = operator.upper()
        if op_upper == "IS NOT NULL":
            where_parts.append(f"{field} IS NOT NULL")
        elif op_upper == "IS NULL":
            where_parts.append(f"{field} IS NULL")
        elif "!=" in operator and value is None:
            where_parts.append(f"{field} {operator}")
        elif op_upper == "IN":
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

    def _build_where_clause(
        self,
        filters: Optional[List[Dict[str, Any]]],
        placeholder: str
    ) -> Tuple[str, List[Any]]:
        """Build WHERE clause combining default_filters and user filters.

        Args:
            filters: User-provided filters
            placeholder: SQL placeholder ("?" for SQLite, "%s" for MySQL)

        Returns:
            Tuple of (where_clause_string, params_list)
        """
        where_parts: List[str] = []
        params: List[Any] = []

        for f in self.default_filters:
            self._apply_single_filter(f, placeholder, where_parts, params)

        for f in (filters or []):
            self._apply_single_filter(f, placeholder, where_parts, params)

        if where_parts:
            return f" WHERE {' AND '.join(where_parts)}", params
        return "", params

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

        # 1. Detect needed JOINs from selected_columns
        needed_joins = self._detect_needed_joins(selected_columns or [])

        # 2. Build auto-JOIN clauses
        auto_join_clauses = []
        for obj_name in needed_joins:
            relationship = self._find_relationship(obj_name)
            if relationship:
                join_clause = self._build_auto_join_clause(relationship)
                if join_clause:
                    auto_join_clauses.append(join_clause)

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

        # Build FROM clause - handle both table and custom query
        if self.custom_query:
            # Wrap custom query as subquery
            query = f"SELECT {columns_str} FROM ({self.custom_query.strip()}) AS {self.object_type}"
        else:
            query = f"SELECT {columns_str} FROM {self.table_name} AS {self.object_type}"
        params: List[Any] = []

        # 3. Add auto-JOIN clauses
        if auto_join_clauses:
            query += " " + " ".join(auto_join_clauses)

        # Build JOIN clause (explicit joins from parameter)
        if joins:
            join_sql = self._build_join_clause(joins)
            if join_sql:
                query += f" {join_sql}"

        # Build WHERE clause using _build_where_clause
        where_clause, where_params = self._build_where_clause(filters, placeholder)
        if where_clause:
            query += where_clause
            params.extend(where_params)

        # Auto-detect aggregate queries and add GROUP BY for non-aggregate columns
        if selected_columns:
            agg_pattern = re.compile(r'^\s*(AVG|SUM|COUNT|MAX|MIN)\s*\(', re.IGNORECASE)
            has_aggregate = any(agg_pattern.match(col) for col in selected_columns)
            if has_aggregate:
                # Non-aggregate columns become GROUP BY columns
                group_cols = [
                    self.resolve_column(col) for col in selected_columns
                    if not agg_pattern.match(col)
                ]
                if group_cols:
                    query += f" GROUP BY {', '.join(group_cols)}"

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
