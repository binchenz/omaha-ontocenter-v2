"""Semantic mapping functions."""

from omaha.core.config.schema import OntologyObjectConfig
from omaha.core.ontology.models import OntologyObject, Table
from omaha.utils.exceptions import OntologyError


def map_ontology_object(obj_config: OntologyObjectConfig, table: Table) -> OntologyObject:
    """Map ontology config to discovered table schema.

    Args:
        obj_config: Ontology object configuration
        table: Discovered table schema

    Returns:
        OntologyObject with mapped properties

    Raises:
        OntologyError: If mapping fails
    """
    # Build property mapping from config
    properties = {}
    for prop in obj_config.properties:
        properties[prop.name] = prop.column

    return OntologyObject(
        name=obj_config.name,
        table=table,
        properties=properties
    )


def validate_mapping(obj: OntologyObject) -> list[str]:
    """Validate that all mapped columns exist in table.

    Args:
        obj: OntologyObject to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Get set of available column names
    available_columns = {col.name for col in obj.table.columns}

    # Check each mapped column
    for prop_name, column_name in obj.properties.items():
        if column_name not in available_columns:
            errors.append(
                f"Property '{prop_name}' maps to non-existent column '{column_name}' "
                f"in table '{obj.table.name}'"
            )

    return errors
