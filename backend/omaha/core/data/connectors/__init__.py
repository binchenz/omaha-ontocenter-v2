"""Data connectors for database access."""

from omaha.core.data.connectors.base import BaseConnector
from omaha.core.data.connectors.postgresql import PostgreSQLConnector
from omaha.core.data.connectors.mysql import MySQLConnector
from omaha.core.config.schema import DataSourceConfig


def create_connector(config: DataSourceConfig) -> BaseConnector:
    """Factory function to create appropriate connector based on config.

    Args:
        config: DataSourceConfig with connection details

    Returns:
        Appropriate connector instance

    Raises:
        ValueError: If datasource type is not supported
    """
    if config.type == "postgresql":
        return PostgreSQLConnector(config)
    elif config.type == "mysql":
        return MySQLConnector(config)
    else:
        raise ValueError(f"Unsupported datasource type: {config.type}")


__all__ = ["BaseConnector", "PostgreSQLConnector", "MySQLConnector", "create_connector"]
