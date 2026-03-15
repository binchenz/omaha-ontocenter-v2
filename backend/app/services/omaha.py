"""
Omaha Core integration service - Simplified for Phase 1.
"""
from typing import Dict, Any, List, Optional
import yaml
import sqlite3
import pymysql
import os


class OmahaService:
    """Service for integrating with Omaha Core."""

    def __init__(self):
        self.ontology_cache: Dict[int, Any] = {}

    def parse_config(self, config_yaml: str) -> Dict[str, Any]:
        """Parse and validate Omaha configuration YAML."""
        try:
            # Parse YAML
            config_dict = yaml.safe_load(config_yaml)

            # Basic validation
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

    def build_ontology(self, config_yaml: str) -> Dict[str, Any]:
        """Build ontology from configuration."""
        try:
            # Parse config
            result = self.parse_config(config_yaml)
            if not result["valid"]:
                return result

            config_dict = result["config"]

            # For Phase 1, return a simplified ontology structure
            # Extract ontology from config if present
            ontology = config_dict.get("ontology", {})

            return {
                "valid": True,
                "ontology": {
                    "objects": ontology.get("objects", {}),
                    "relationships": ontology.get("relationships", []),
                },
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }

    def get_object_schema(
        self, config_yaml: str, object_type: str
    ) -> Dict[str, Any]:
        """Get schema (columns) for an object type."""
        try:
            # Parse config
            result = self.parse_config(config_yaml)
            if not result["valid"]:
                return {"success": False, "error": "Invalid configuration"}

            config = result["config"]

            # Find the object definition
            ontology = config.get("ontology", {})
            objects = ontology.get("objects", [])

            obj_def = None
            for obj in objects:
                if obj.get("name") == object_type:
                    obj_def = obj
                    break

            if not obj_def:
                return {
                    "success": False,
                    "error": f"Object type '{object_type}' not found in ontology",
                }

            # Extract properties/columns
            properties = obj_def.get("properties", [])
            columns = []

            for prop in properties:
                columns.append(
                    {
                        "name": prop.get("column") or prop.get("name"),
                        "type": prop.get("type", "string"),
                        "description": prop.get("description", ""),
                    }
                )

            return {"success": True, "columns": columns}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def query_objects(
        self,
        config_yaml: str,
        object_type: str,
        selected_columns: Optional[List[str]] = None,
        filters: Optional[List[Dict[str, Any]]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Query objects using Omaha Core."""
        try:
            # Parse config
            result = self.parse_config(config_yaml)
            if not result["valid"]:
                return {"success": False, "error": "Invalid configuration"}

            config = result["config"]

            # Find the object definition
            ontology = config.get("ontology", {})
            objects = ontology.get("objects", [])

            obj_def = None
            for obj in objects:
                if obj.get("name") == object_type:
                    obj_def = obj
                    break

            if not obj_def:
                return {
                    "success": False,
                    "error": f"Object type '{object_type}' not found in ontology"
                }

            # Get datasource
            datasource_id = obj_def.get("datasource")
            datasources = config.get("datasources", [])

            ds_config = None
            for ds in datasources:
                if ds.get("id") == datasource_id:
                    ds_config = ds
                    break

            if not ds_config:
                return {
                    "success": False,
                    "error": f"Datasource '{datasource_id}' not found"
                }

            ds_type = ds_config.get("type")
            table_name = obj_def.get("table")

            # Connect to database based on type
            if ds_type == "sqlite":
                data = self._query_sqlite(
                    ds_config, table_name, selected_columns, filters, limit
                )
            elif ds_type == "mysql":
                data = self._query_mysql(
                    ds_config, table_name, selected_columns, filters, limit
                )
            else:
                return {
                    "success": False,
                    "error": f"Unsupported datasource type: {ds_type}"
                }

            return {
                "success": True,
                "data": data,
                "count": len(data),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _build_where_clause(
        self, filters: List[Dict[str, Any]], db_type: str
    ) -> tuple[str, List[Any]]:
        """Build WHERE clause from filters."""
        conditions = []
        params = []
        placeholder = "?" if db_type == "sqlite" else "%s"

        for f in filters:
            field = f.get("field")
            operator = f.get("operator", "=")
            value = f.get("value")

            if operator.upper() == "IN":
                # Handle IN operator
                values = [v.strip() for v in str(value).split(",")]
                placeholders = ",".join([placeholder] * len(values))
                conditions.append(f"{field} IN ({placeholders})")
                params.extend(values)
            elif operator.upper() == "LIKE":
                # Handle LIKE operator
                conditions.append(f"{field} LIKE {placeholder}")
                params.append(f"%{value}%")
            else:
                # Handle standard operators (=, >, <, >=, <=, !=)
                conditions.append(f"{field} {operator} {placeholder}")
                params.append(value)

        where_clause = " AND ".join(conditions) if conditions else ""
        return where_clause, params

    def _query_sqlite(
        self,
        ds_config: Dict[str, Any],
        table_name: str,
        selected_columns: Optional[List[str]],
        filters: Optional[List[Dict[str, Any]]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Query SQLite database."""
        # Get database path
        db_path = ds_config.get("connection", {}).get("database")
        if not db_path:
            raise ValueError("Database path not specified")

        # Make path absolute if relative
        if not os.path.isabs(db_path):
            db_path = os.path.abspath(db_path)

        if not os.path.exists(db_path):
            raise ValueError(f"Database file not found: {db_path}")

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Build query with column selection
        if selected_columns:
            columns_str = ", ".join(selected_columns)
        else:
            columns_str = "*"

        query = f"SELECT {columns_str} FROM {table_name}"
        params = []

        # Build WHERE clause from filters
        if filters:
            where_clause, params = self._build_where_clause(filters, "sqlite")
            if where_clause:
                query += f" WHERE {where_clause}"

        query += f" LIMIT {limit}"

        # Execute query
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()
        data = [dict(row) for row in rows]
        conn.close()

        return data

    def _query_mysql(
        self,
        ds_config: Dict[str, Any],
        table_name: str,
        selected_columns: Optional[List[str]],
        filters: Optional[List[Dict[str, Any]]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Query MySQL database."""
        connection_config = ds_config.get("connection", {})

        conn = pymysql.connect(
            host=connection_config.get("host"),
            port=connection_config.get("port", 3306),
            user=connection_config.get("user"),
            password=connection_config.get("password"),
            database=connection_config.get("database"),
            connect_timeout=10,
            charset='utf8mb4'
        )

        cursor = conn.cursor(pymysql.cursors.DictCursor)

        # Build query with column selection
        if selected_columns:
            columns_str = ", ".join(selected_columns)
        else:
            columns_str = "*"

        query = f"SELECT {columns_str} FROM {table_name}"
        params = []

        # Build WHERE clause from filters
        if filters:
            where_clause, params = self._build_where_clause(filters, "mysql")
            if where_clause:
                query += f" WHERE {where_clause}"

        query += f" LIMIT {limit}"

        # Execute query
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        rows = cursor.fetchall()

        # Convert datetime/date objects to strings
        data = []
        for row in rows:
            converted_row = {}
            for key, value in row.items():
                if hasattr(value, 'isoformat'):
                    converted_row[key] = value.isoformat()
                else:
                    converted_row[key] = value
            data.append(converted_row)

        conn.close()
        return data

    def analyze_pricing(
        self, config_yaml: str, object_type: str
    ) -> Dict[str, Any]:
        """Analyze pricing for objects."""
        try:
            # For Phase 1, return placeholder
            return {
                "success": True,
                "metrics": {},
                "message": "Pricing analysis placeholder - to be implemented in Phase 2"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


omaha_service = OmahaService()
