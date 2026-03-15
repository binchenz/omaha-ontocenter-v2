"""
Omaha Core integration service - Simplified for Phase 1.
"""
from typing import Dict, Any, List, Optional
import yaml
import sqlite3
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

            # Only support SQLite for now
            if ds_config.get("type") != "sqlite":
                return {
                    "success": False,
                    "error": f"Unsupported datasource type: {ds_config.get('type')}"
                }

            # Get database path
            db_path = ds_config.get("connection", {}).get("database")
            if not db_path:
                return {
                    "success": False,
                    "error": "Database path not specified"
                }

            # Make path absolute if relative
            if not os.path.isabs(db_path):
                db_path = os.path.abspath(db_path)

            if not os.path.exists(db_path):
                return {
                    "success": False,
                    "error": f"Database file not found: {db_path}"
                }

            # Query the database
            table_name = obj_def.get("table")

            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Build query
            query = f"SELECT * FROM {table_name}"

            # Add filters if provided (filters is a dict of field: value)
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

            # Convert to list of dicts
            data = []
            for row in rows:
                data.append(dict(row))

            conn.close()

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
