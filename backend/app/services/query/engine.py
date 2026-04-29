"""QueryEngine — generic ontology query service."""
from typing import Dict, Any, List, Optional, Tuple
import os
import re

import yaml

from app.services.semantic.service import semantic_service


def _find_by_name(items: List[Dict[str, Any]], name: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'name' key."""
    return next((item for item in items if item.get("name") == name), None)


def _find_by_id(items: List[Dict[str, Any]], item_id: str) -> Optional[Dict[str, Any]]:
    """Find an item in a list of dicts by its 'id' key."""
    return next((item for item in items if item.get("id") == item_id), None)


class QueryEngine:
    """Generic ontology query engine."""

    def __init__(self, config_yaml: str = None):
        self.config_yaml = config_yaml

    def parse_config(self, config_yaml: str = None) -> Dict[str, Any]:
        """Parse and validate Omaha configuration YAML."""
        config_yaml = config_yaml or self.config_yaml
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


OmahaService = QueryEngine

query_engine = QueryEngine()
omaha_service = query_engine
