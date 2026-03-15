"""Query executor for data sources."""

import pandas as pd

from omaha.core.config.schema import DataSourceConfig
from omaha.core.data.connectors.base import BaseConnector
from omaha.core.data.connectors.postgresql import PostgreSQLConnector
from omaha.core.data.connectors.mysql import MySQLConnector
from omaha.utils.exceptions import DataSourceError


def create_connector(datasource: DataSourceConfig) -> BaseConnector:
    """Factory function to create appropriate connector.

    Args:
        datasource: DataSourceConfig containing connection details

    Returns:
        Appropriate connector instance based on datasource type

    Raises:
        DataSourceError: If datasource type is not supported
    """
    if datasource.type == "postgresql":
        return PostgreSQLConnector(datasource)
    elif datasource.type == "mysql":
        return MySQLConnector(datasource)
    else:
        raise DataSourceError(
            f"Unsupported datasource type: {datasource.type}",
            context={"datasource_id": datasource.id, "type": datasource.type}
        )


def execute_query(datasource: DataSourceConfig, query: str) -> pd.DataFrame:
    """Execute query on datasource and return results.

    This is a convenience function that creates a connector, executes
    the query, and properly cleans up the connection.

    Args:
        datasource: DataSourceConfig containing connection details
        query: SQL query string

    Returns:
        DataFrame containing query results

    Raises:
        DataSourceError: If datasource type is not supported
        DatabaseConnectionError: If connection fails
        QueryError: If query execution fails
    """
    connector = create_connector(datasource)

    with connector:
        result = connector.execute_query(query)

    return result
