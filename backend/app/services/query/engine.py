"""
QueryEngine — generic ontology query service.

Formerly OmahaService in services/legacy/financial/omaha.py.
Tushare-specific methods have been removed; the engine now routes
exclusively through the connector registry.
"""
from typing import Dict, Any, List, Optional, Tuple
import operator as op
import os
import re
import sqlite3

import pymysql
import pandas as pd
import yaml

from app.services.semantic.service import semantic_service
from app.services.query.builder import SemanticQueryBuilder
from app.services.semantic.computed_property import ComputedPropertyEngine
from app.services.semantic.formatter import SemanticTypeFormatter


# Operator lookup for client-side DataFrame filtering
_DF_OPS = {
    "=": op.eq, "==": op.eq,
    "!=": op.ne,
    ">": op.gt, ">=": op.ge,
    "<": op.lt, "<=": op.le,
}


def _find_by_name(items: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'name' key."""
    return next((item for item in items if item.get("name") == name), None)


def _find_by_id(items: List[Dict[str, Any]], item_id: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'id' key."""
    return next((item for item in items if item.get("id") == item_id), None)


class QueryEngine:
    """Generic ontology query engine.

    Replaces the legacy OmahaService; compatible alias ``OmahaService`` is
    provided below for backwards compatibility during migration.
    """

    def __init__(self, config_yaml: str = None):
        self.config_yaml = config_yaml

    def parse_config(self, config_yaml: str = None) -> Dict[str, Any]:
        config_yaml = config_yaml or self.config_yaml
        """Parse and validate Omaha configuration YAML."""
        try:
            # Substitute environment variables in YAML before parsing
            # Pattern: ${VAR_NAME} (uppercase only)
            def substitute_env_vars(text: str) -> str:
                """Replace ${VAR_NAME} patterns with environment variable values."""
                pattern = r'\$\{([A-Z_][A-Z0-9_]*)\}'
                def replacer(match):
                    var_name = match.group(1)
                    return os.environ.get(var_name, match.group(0))
                return re.sub(pattern, replacer, text)

            config_yaml = substitute_env_vars(config_yaml)
            config_dict = yaml.safe_load(config_yaml)

            if not isinstance(config_dict, dict):
                return {
                    "valid": False,
                    "errors": ["Configuration must be a YAML dictionary"],
                    "warnings": [],
                }

            return {
                "valid": True,
                "errors": [],
                "warnings": [],
                "config": config_dict,
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "warnings": [],
            }

    def _parse_ontology(
        self, config_yaml: str = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Parse config and return (config_dict, ontology_dict, error_response).

        Error is None on success.
        """
        config_yaml = config_yaml or self.config_yaml
        result = self.parse_config(config_yaml)
        if not result["valid"]:
            return None, None, result
        config = result["config"]
        return config, config.get("ontology", {}), None

    def _find_object(
        self, config_yaml: str = None, object_type: str = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Parse config and find object definition.

        Returns (config, ontology, obj_def, error_response).
        """
        config_yaml = config_yaml or self.config_yaml
        if not config_yaml:
            return None, None, None, {"success": False, "error": "No configuration provided"}
        if not object_type:
            return None, None, None, {"success": False, "error": "object_type required"}
        config, ontology, err = self._parse_ontology(config_yaml)
        if err:
            return None, None, None, {"success": False, "error": "Invalid configuration"}
        objects = ontology.get("objects", [])
        obj_def = _find_by_name(objects, object_type)
        if not obj_def:
            return None, None, None, {
                "success": False,
                "error": f"Object type '{object_type}' not found in ontology",
            }
        return config, ontology, obj_def, None

    def build_ontology(self, config_yaml: str = None) -> Dict[str, Any]:
        """Build ontology from configuration."""
        config_yaml = config_yaml or self.config_yaml
        try:
            _, ontology, err = self._parse_ontology(config_yaml)
            if err:
                return err
            objects = ontology.get("objects", [])
            relationships = ontology.get("relationships", [])
            return {
                "valid": True,
                "ontology": {
                    "objects": objects,
                    "relationships": relationships,
                },
                "objects": objects,
                "relationships": relationships,
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}

    def get_relationships(
        self, config_yaml: str, object_type: str
    ) -> List[Dict[str, Any]]:
        """Get available relationships for an object type."""
        try:
            _, ontology, err = self._parse_ontology(config_yaml)
            if err:
                return []

            available = []
            for rel in ontology.get("relationships", []):
                if rel.get("from_object") == object_type:
                    available.append({
                        "name": rel.get("name"),
                        "description": rel.get("description", ""),
                        "from_object": rel.get("from_object"),
                        "to_object": rel.get("to_object"),
                        "type": rel.get("type"),
                        "join_condition": rel.get("join_condition"),
                        "direction": "forward",
                    })
                elif rel.get("to_object") == object_type:
                    join_cond = rel.get("join_condition", {})
                    available.append({
                        "name": rel.get("name"),
                        "description": rel.get("description", ""),
                        "from_object": rel.get("to_object"),
                        "to_object": rel.get("from_object"),
                        "type": rel.get("type"),
                        "join_condition": {
                            "from_field": join_cond.get("to_field"),
                            "to_field": join_cond.get("from_field"),
                        },
                        "direction": "reverse",
                    })
            return available
        except Exception:
            return []

    def get_object_schema(
        self, config_yaml: str = None, object_type: str = None
    ) -> Dict[str, Any]:
        """Get schema (columns) for an object type, enriched with semantic metadata."""
        if object_type is None and config_yaml is not None and self.config_yaml is not None:
            # Single positional argument is object_type
            object_type = config_yaml
            config_yaml = None
        config_yaml = config_yaml or self.config_yaml
        if not config_yaml or not object_type:
            return {"success": False, "error": "config_yaml and object_type are required"}
        try:
            result = semantic_service.get_schema_with_semantics(config_yaml, object_type)
            if result.get("success"):
                result["name"] = result.get("object_type", object_type)
                result["fields"] = result.get("columns", [])
                return result
            # Fallback to basic schema
            _, _, obj_def, err = self._find_object(config_yaml, object_type)
            if err:
                return err
            source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")
            fields = [
                {
                    "name": prop.get("column") or prop.get("name"),
                    "type": prop.get("type", "string"),
                    "description": prop.get("description", ""),
                }
                for prop in obj_def.get("properties", [])
            ]
            return {
                "success": True,
                "name": object_type,
                "object_type": object_type,
                "source_entity": source_entity,
                "fields": fields,
                "columns": fields,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_join_clause(
        self,
        joins: List[Dict[str, Any]],
        relationships: List[Dict[str, Any]],
        objects: List[Dict[str, Any]],
    ) -> str:
        """Build JOIN clause from join configurations."""
        if not joins:
            return ""

        join_clauses = []
        for join_config in joins:
            relationship = _find_by_name(relationships, join_config.get("relationship_name"))
            if not relationship:
                continue

            to_object = _find_by_name(objects, relationship.get("to_object"))
            if not to_object:
                continue

            to_table = to_object.get("table")
            join_condition = relationship.get("join_condition", {})
            from_field = join_condition.get("from_field")
            to_field = join_condition.get("to_field")

            if not all([to_table, from_field, to_field]):
                continue

            join_type = join_config.get("join_type", "LEFT").upper()
            from_obj = relationship.get("from_object")
            to_obj = relationship.get("to_object")
            join_clauses.append(
                f"{join_type} JOIN {to_table} AS {to_obj}"
                f" ON {from_obj}.{from_field} = {to_obj}.{to_field}"
            )

        return " ".join(join_clauses)

    def query_objects(
        self,
        config_yaml: str = None,
        object_type: str = None,
        selected_columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        joins: Optional[List[Dict[str, Any]]] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Query objects using the connector registry."""
        if object_type is None and config_yaml is not None and self.config_yaml is not None:
            # Single positional argument is object_type
            object_type = config_yaml
            config_yaml = None
        config_yaml = config_yaml or self.config_yaml
        if not config_yaml:
            return {"success": False, "error": "No configuration provided"}
        if not object_type:
            return {"success": False, "error": "object_type required"}
        try:
            config, ontology, obj_def, err = self._find_object(config_yaml, object_type)
            if err:
                return err

            datasource_id = obj_def.get("datasource")
            ds_config = _find_by_id(config.get("datasources", []), datasource_id)
            if not ds_config:
                return {"success": False, "error": f"Datasource '{datasource_id}' not found"}

            return self._query_connector(obj_def, ds_config, selected_columns, filters, limit)
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _query_connector(self, obj_def, ds_config, selected_columns, filters, limit):
        from app.connectors.registry import get_connector
        source_entity = obj_def.get("source_entity") or obj_def.get("api_name", "")
        connector = get_connector(ds_config["type"], ds_config.get("connection", {}))
        try:
            raw_data = connector.query(
                source=source_entity,
                columns=selected_columns,
                filters=filters,
                limit=limit,
            )
            return {"success": True, "data": raw_data, "count": len(raw_data)}
        finally:
            connector.close()

    def _build_where_clause(
        self, filters: List[Dict[str, Any]], db_type: str
    ) -> Tuple[str, List[Any]]:
        """Build WHERE clause from filters."""
        conditions: List[str] = []
        params: List[Any] = []
        placeholder = "?" if db_type == "sqlite" else "%s"

        for f in filters:
            field = f.get("field")
            operator = f.get("operator", "=")
            value = f.get("value")

            op_upper = operator.upper()
            if op_upper == "IN":
                values = [v.strip() for v in str(value).split(",")]
                placeholders = ",".join([placeholder] * len(values))
                conditions.append(f"{field} IN ({placeholders})")
                params.extend(values)
            elif op_upper == "LIKE":
                conditions.append(f"{field} LIKE {placeholder}")
                params.append(f"%{value}%")
            else:
                conditions.append(f"{field} {operator} {placeholder}")
                params.append(value)

        return " AND ".join(conditions), params

    def _build_query_from_custom(
        self,
        custom_query: str,
        object_type: str,
        selected_columns: Optional[List[str]],
        filters: Optional[List[Dict[str, Any]]],
        limit: int,
        db_type: str,
    ) -> Tuple[str, List[Any]]:
        """Build query from custom SQL query definition."""
        params: List[Any] = []

        if selected_columns:
            columns_str = ", ".join(selected_columns)
        else:
            columns_str = "*"

        query = f"SELECT {columns_str} FROM ({custom_query.strip()}) AS {object_type}"

        if filters:
            where_clause, params = self._build_where_clause(filters, db_type)
            if where_clause:
                query += f" WHERE {where_clause}"

        if limit is not None:
            query += f" LIMIT {limit}"

        return query, params

    def _build_select_query(
        self,
        table_name: str,
        object_type: str,
        selected_columns: Optional[List[str]],
        filters: Optional[List[Dict[str, Any]]],
        joins: Optional[List[Dict[str, Any]]],
        relationships: List[Dict[str, Any]],
        objects: List[Dict[str, Any]],
        limit: int,
        db_type: str,
    ) -> Tuple[str, List[Any]]:
        """Build a SELECT query string and parameter list."""
        columns_str = ", ".join(selected_columns) if selected_columns else "*"
        query = f"SELECT {columns_str} FROM {table_name} AS {object_type}"
        params: List[Any] = []

        if joins:
            join_clause = self._build_join_clause(joins, relationships, objects)
            if join_clause:
                query += f" {join_clause}"

        if filters:
            where_clause, params = self._build_where_clause(filters, db_type)
            if where_clause:
                query += f" WHERE {where_clause}"

        if limit is not None:
            query += f" LIMIT {limit}"
        return query, params

    def _connect_sqlite(self, ds_config: Dict[str, Any]) -> sqlite3.Connection:
        """Create a SQLite connection from datasource config."""
        db_path = ds_config.get("connection", {}).get("database")
        if not db_path:
            raise ValueError("Database path not specified")

        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)

        if not os.path.exists(db_path):
            raise ValueError(f"Database file not found: {db_path}")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _connect_mysql(self, ds_config: Dict[str, Any]) -> pymysql.connections.Connection:
        """Create a MySQL connection from datasource config."""
        connection_config = ds_config.get("connection", {})
        return pymysql.connect(
            host=connection_config.get("host"),
            port=connection_config.get("port", 3306),
            user=connection_config.get("user"),
            password=connection_config.get("password"),
            database=connection_config.get("database"),
            connect_timeout=10,
            charset="utf8mb4",
        )

    def _format_data_with_semantic_types(
        self, df: pd.DataFrame, obj_def: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Format data with semantic types."""
        if df.empty:
            return []

        all_props = obj_def.get('properties', []) + obj_def.get('computed_properties', [])
        semantic_type_map = {
            prop['name']: prop['semantic_type']
            for prop in all_props
            if 'semantic_type' in prop
        }

        data = df.to_dict('records')

        if semantic_type_map:
            formatter = SemanticTypeFormatter()
            for record in data:
                for field, semantic_type in semantic_type_map.items():
                    if field in record:
                        record[field] = formatter.format_value(
                            record[field], semantic_type
                        )

        return data

    def _execute_query(
        self, ds_config: Dict[str, Any], ds_type: str, query: str, params: List[Any]
    ) -> List[Dict[str, Any]]:
        """Execute a query against the appropriate database backend."""
        if ds_type == "sqlite":
            conn = self._connect_sqlite(ds_config)
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
            finally:
                conn.close()

        conn = self._connect_mysql(ds_config)
        try:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, params)
            return [
                {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in row.items()}
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def analyze_pricing(
        self, config_yaml: str, object_type: str
    ) -> Dict[str, Any]:
        """Analyze pricing for objects."""
        return {
            "success": True,
            "metrics": {},
            "message": "Pricing analysis placeholder - to be implemented in Phase 2",
        }


# Backwards-compatibility alias — prefer QueryEngine in new code.
OmahaService = QueryEngine

query_engine = QueryEngine()
# Legacy module-level alias used by older import sites.
omaha_service = query_engine
