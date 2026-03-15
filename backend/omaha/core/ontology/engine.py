"""Main ontology engine."""

from omaha.core.config.schema import RootConfig
from omaha.core.ontology.models import OntologyObject
from omaha.core.ontology.discovery import discover_table
from omaha.core.ontology.mapper import map_ontology_object, validate_mapping
from omaha.core.data.executor import create_connector
from omaha.utils.exceptions import OntologyError


class OntologyEngine:
    """Ontology engine for building and managing ontology."""

    def __init__(self, config: RootConfig):
        """Initialize with configuration.

        Args:
            config: Root configuration object
        """
        self.config = config
        self._ontology: dict[str, OntologyObject] = {}

    def build_ontology(self) -> dict[str, OntologyObject]:
        """Build complete ontology from config and database.

        Discovers database schemas and maps them to ontology objects
        defined in configuration.

        Returns:
            Dictionary mapping object names to OntologyObject instances

        Raises:
            OntologyError: If ontology building fails
        """
        self._ontology = {}

        # Build datasource lookup
        datasources = {ds.id: ds for ds in self.config.datasources}

        # Process each ontology object
        for obj_config in self.config.ontology.objects:
            # Get datasource config
            ds_config = datasources.get(obj_config.datasource)
            if not ds_config:
                raise OntologyError(
                    f"Datasource '{obj_config.datasource}' not found for object '{obj_config.name}'",
                    context={"object": obj_config.name, "datasource": obj_config.datasource}
                )

            # Create connector and discover table
            connector = create_connector(ds_config)
            try:
                with connector:
                    table = discover_table(connector, obj_config.table)
            except Exception as e:
                raise OntologyError(
                    f"Failed to discover table '{obj_config.table}' for object '{obj_config.name}': {str(e)}",
                    context={"object": obj_config.name, "table": obj_config.table, "error": str(e)}
                )

            # Map ontology object
            ontology_obj = map_ontology_object(obj_config, table)

            # Validate mapping
            errors = validate_mapping(ontology_obj)
            if errors:
                raise OntologyError(
                    f"Mapping validation failed for object '{obj_config.name}': {'; '.join(errors)}",
                    context={"object": obj_config.name, "errors": errors}
                )

            # Store in ontology
            self._ontology[obj_config.name] = ontology_obj

        return self._ontology

    def get_object(self, name: str) -> OntologyObject:
        """Get ontology object by name.

        Args:
            name: Name of the ontology object

        Returns:
            OntologyObject instance

        Raises:
            OntologyError: If object not found
        """
        if name not in self._ontology:
            raise OntologyError(
                f"Ontology object '{name}' not found",
                context={"object": name, "available": list(self._ontology.keys())}
            )
        return self._ontology[name]
