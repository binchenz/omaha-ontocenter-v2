"""Schema discovery functions."""

from omaha.core.data.connectors.base import BaseConnector
from omaha.core.ontology.models import Column, Table
from omaha.utils.exceptions import SchemaDiscoveryError


def discover_schema(connector: BaseConnector) -> list[Table]:
    """Discover all tables and columns from database.

    Args:
        connector: Database connector instance

    Returns:
        List of discovered tables with their columns

    Raises:
        SchemaDiscoveryError: If schema discovery fails
    """
    try:
        table_names = connector.get_tables()
        tables = []

        for table_name in table_names:
            table = discover_table(connector, table_name)
            tables.append(table)

        return tables
    except Exception as e:
        raise SchemaDiscoveryError(
            f"Failed to discover schema: {str(e)}",
            context={"error": str(e)}
        )


def discover_table(connector: BaseConnector, table_name: str) -> Table:
    """Discover schema for a specific table.

    Args:
        connector: Database connector instance
        table_name: Name of the table to discover

    Returns:
        Table object with column metadata

    Raises:
        SchemaDiscoveryError: If table discovery fails
    """
    try:
        column_metadata = connector.get_columns(table_name)
        columns = [
            Column(
                name=col["name"],
                type=col["type"],
                nullable=col["nullable"]
            )
            for col in column_metadata
        ]

        return Table(name=table_name, columns=columns)
    except Exception as e:
        raise SchemaDiscoveryError(
            f"Failed to discover table '{table_name}': {str(e)}",
            context={"table": table_name, "error": str(e)}
        )
