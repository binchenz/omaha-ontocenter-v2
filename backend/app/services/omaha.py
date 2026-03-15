"""
Omaha Core integration service - Simplified for Phase 1.
"""
from typing import Dict, Any, List, Optional, Tuple
import yaml
import sqlite3
import pymysql
import os

from app.services.semantic import semantic_service


def _find_by_name(items: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'name' key."""
    return next((item for item in items if item.get("name") == name), None)


def _find_by_id(items: List[Dict[str, Any]], item_id: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'id' key."""
    return next((item for item in items if item.get("id") == item_id), None)


class OmahaService:
    """Service for integrating with Omaha Core."""

    def parse_config(self, config_yaml: str) -> Dict[str, Any]:
        """Parse and validate Omaha configuration YAML."""
        try:
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
        self, config_yaml: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Parse config and return (config_dict, ontology_dict, error_response).

        Error is None on success.
        """
        result = self.parse_config(config_yaml)
        if not result["valid"]:
            return None, None, result
        config = result["config"]
        return config, config.get("ontology", {}), None

    def _find_object(
        self, config_yaml: str, object_type: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """Parse config and find object definition.

        Returns (config, ontology, obj_def, error_response).
        """
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

    def build_ontology(self, config_yaml: str) -> Dict[str, Any]:
        """Build ontology from configuration."""
        try:
            _, ontology, err = self._parse_ontology(config_yaml)
            if err:
                return err
            return {
                "valid": True,
                "ontology": {
                    "objects": ontology.get("objects", {}),
                    "relationships": ontology.get("relationships", []),
                },
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
        self, config_yaml: str, object_type: str
    ) -> Dict[str, Any]:
        """Get schema (columns) for an object type, enriched with semantic metadata."""
        try:
            result = semantic_service.get_schema_with_semantics(config_yaml, object_type)
            if result.get("success"):
                return result
            # Fallback to basic schema
            _, _, obj_def, err = self._find_object(config_yaml, object_type)
            if err:
                return err
            columns = [
                {
                    "name": prop.get("column") or prop.get("name"),
                    "type": prop.get("type", "string"),
                    "description": prop.get("description", ""),
                }
                for prop in obj_def.get("properties", [])
            ]
            return {"success": True, "columns": columns}
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
        config_yaml: str,
        object_type: str,
        selected_columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        joins: Optional[List[Dict[str, Any]]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Query objects using Omaha Core."""
        try:
            config, ontology, obj_def, err = self._find_object(config_yaml, object_type)
            if err:
                return err

            datasource_id = obj_def.get("datasource")
            ds_config = _find_by_id(config.get("datasources", []), datasource_id)
            if not ds_config:
                return {"success": False, "error": f"Datasource '{datasource_id}' not found"}

            ds_type = ds_config.get("type")
            if ds_type not in ("sqlite", "mysql"):
                return {"success": False, "error": f"Unsupported datasource type: {ds_type}"}

            objects = ontology.get("objects", [])
            relationships = ontology.get("relationships", [])
            table_name = obj_def.get("table")

            query, params = self._build_select_query(
                table_name, object_type, selected_columns, filters,
                joins, relationships, objects, limit, ds_type,
            )
            data = self._execute_query(ds_config, ds_type, query, params)

            return {"success": True, "data": data, "count": len(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}

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


omaha_service = OmahaService()
