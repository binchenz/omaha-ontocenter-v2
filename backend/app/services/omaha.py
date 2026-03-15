"""
Omaha Core integration service.
"""
from typing import Dict, Any, List, Optional
import yaml
from io import StringIO

# Import from Omaha Core
from omaha.core.config.loader import load_config
from omaha.core.config.validator import validate_config
from omaha.core.ontology.engine import OntologyEngine
from omaha.core.data.executor import get_executor
from omaha.core.data.fetcher import DataFetcher
from omaha.core.analysis.engine import AnalysisEngine


class OmahaService:
    """Service for integrating with Omaha Core."""

    def __init__(self):
        self.ontology_cache: Dict[int, Any] = {}

    def parse_config(self, config_yaml: str) -> Dict[str, Any]:
        """Parse and validate Omaha configuration YAML."""
        try:
            # Load configuration
            config = load_config(StringIO(config_yaml))

            # Validate configuration
            validation_result = validate_config(config)

            if validation_result.errors:
                return {
                    "valid": False,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                }

            return {
                "valid": True,
                "errors": [],
                "warnings": validation_result.warnings,
                "config": config,
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

            config = result["config"]

            # Build ontology
            engine = OntologyEngine(config)
            ontology = engine.build_ontology()

            # Convert to dict for JSON serialization
            ontology_dict = {
                "objects": {},
                "relationships": [],
            }

            for obj_name, obj in ontology.objects.items():
                ontology_dict["objects"][obj_name] = {
                    "name": obj.name,
                    "table_name": obj.table.name if obj.table else None,
                    "properties": [
                        {
                            "name": prop.name,
                            "type": prop.type,
                            "column_name": prop.column.name if prop.column else None,
                        }
                        for prop in obj.properties
                    ],
                }

            for rel in ontology.relationships:
                ontology_dict["relationships"].append(
                    {
                        "name": rel.name,
                        "type": rel.type,
                        "from_object": rel.from_object,
                        "to_object": rel.to_object,
                    }
                )

            return {
                "valid": True,
                "ontology": ontology_dict,
            }
        except Exception as e:
            return {
                "valid": False,
                "errors": [str(e)],
            }

    def query_objects(
        self,
        config_yaml: str,
        object_type: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Query objects from database using ontology."""
        try:
            # Parse config
            result = self.parse_config(config_yaml)
            if not result["valid"]:
                return result

            config = result["config"]

            # Build ontology
            engine = OntologyEngine(config)
            ontology = engine.build_ontology()

            # Get object
            if object_type not in ontology.objects:
                return {
                    "success": False,
                    "error": f"Object type '{object_type}' not found in ontology",
                }

            obj = ontology.objects[object_type]

            # Get datasource
            datasource_name = obj.table.datasource if obj.table else None
            if not datasource_name:
                return {
                    "success": False,
                    "error": f"No datasource found for object '{object_type}'",
                }

            datasource_config = None
            for ds in config.datasources:
                if ds.name == datasource_name:
                    datasource_config = ds
                    break

            if not datasource_config:
                return {
                    "success": False,
                    "error": f"Datasource '{datasource_name}' not found",
                }

            # Execute query
            with get_executor(datasource_config) as executor:
                # Build simple SELECT query
                table_name = obj.table.name
                columns = [prop.column.name for prop in obj.properties if prop.column]

                # Build WHERE clause from filters
                where_clause = ""
                if filters:
                    conditions = []
                    for key, value in filters.items():
                        # Find property
                        prop = next((p for p in obj.properties if p.name == key), None)
                        if prop and prop.column:
                            if isinstance(value, str):
                                conditions.append(f"{prop.column.name} = '{value}'")
                            else:
                                conditions.append(f"{prop.column.name} = {value}")
                    if conditions:
                        where_clause = " WHERE " + " AND ".join(conditions)

                query = f"SELECT {', '.join(columns)} FROM {table_name}{where_clause} LIMIT {limit}"

                result = executor.execute(query)

                # Fetch data
                fetcher = DataFetcher(config, ontology)
                data = fetcher.fetch_object_data(object_type, result)

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
        self,
        config_yaml: str,
        object_type: str,
    ) -> Dict[str, Any]:
        """Analyze pricing for an object type."""
        try:
            # Parse config
            result = self.parse_config(config_yaml)
            if not result["valid"]:
                return result

            config = result["config"]

            # Build ontology
            engine = OntologyEngine(config)
            ontology = engine.build_ontology()

            # Query data
            query_result = self.query_objects(config_yaml, object_type, limit=10000)
            if not query_result.get("success"):
                return query_result

            data = query_result["data"]

            # Analyze
            analysis_engine = AnalysisEngine(config, ontology)
            metrics = analysis_engine.compute_pricing_metrics(object_type, data)

            return {
                "success": True,
                "metrics": metrics,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


omaha_service = OmahaService()
