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

    def query_objects(
        self,
        config_yaml: str,
        object_type: str,
        filters: Optional[Dict[str, Any]] = None,
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
                data = self._query_sqlite(ds_config, table_name, filters, limit)
            elif ds_type == "mysql":
                data = self._query_mysql(ds_config, table_name, filters, limit)
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

    def _query_sqlite(
        self,
        ds_config: Dict[str, Any],
        table_name: str,
        filters: Optional[Dict[str, Any]],
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

        # Build query
        query = f"SELECT * FROM {table_name}"
        params = []

        if filters:
            conditions = []
            for field, value in filters.items():
                conditions.append(f"{field} = ?")
                params.append(value)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

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
        filters: Optional[Dict[str, Any]],
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

        # Build query
        query = f"SELECT * FROM {table_name}"
        params = []

        if filters:
            conditions = []
            for field, value in filters.items():
                conditions.append(f"{field} = %s")
                params.append(value)
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

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
