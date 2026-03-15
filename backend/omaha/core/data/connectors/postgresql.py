"""PostgreSQL database connector implementation."""

from typing import Any, Optional
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, Connection
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import SQLAlchemyError

from omaha.core.config.schema import DataSourceConfig
from omaha.core.data.connectors.base import BaseConnector
from omaha.utils.exceptions import DatabaseConnectionError, DataSourceError, QueryError

# Query truncation length for error messages
QUERY_TRUNCATE_LENGTH = 200


class PostgreSQLConnector(BaseConnector):
    """PostgreSQL database connector."""

    def __init__(self, config: DataSourceConfig):
        """Initialize with connection config.

        Args:
            config: DataSourceConfig containing connection details
        """
        self.config = config
        self.engine: Optional[Engine] = None
        self.connection: Optional[Connection] = None

    def connect(self) -> None:
        """Establish database connection.

        Raises:
            DatabaseConnectionError: If connection fails
        """
        # Close existing connections if any
        if self.connection or self.engine:
            self.disconnect()

        try:
            # Build connection URL securely using URL.create()
            conn_config = self.config.connection
            url = URL.create(
                drivername="postgresql",
                username=conn_config.user,
                password=conn_config.password.get_secret_value(),
                host=conn_config.host,
                port=conn_config.port,
                database=conn_config.database,
            )

            # Create engine with connection pool configuration
            self.engine = create_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
            )
            self.connection = self.engine.connect()

        except SQLAlchemyError as e:
            raise DatabaseConnectionError(
                f"Failed to connect to database: {str(e)}",
                context={
                    "datasource_id": self.config.id,
                    "host": self.config.connection.host,
                    "database": self.config.connection.database,
                }
            ) from e

    def disconnect(self) -> None:
        """Close database connection."""
        # Use try-finally to ensure both resources are cleaned up
        # Suppress exceptions to ensure cleanup completes
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass  # Suppress exceptions during cleanup
            finally:
                self.connection = None

        if self.engine:
            try:
                self.engine.dispose()
            except Exception:
                pass  # Suppress exceptions during cleanup
            finally:
                self.engine = None

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query string

        Returns:
            DataFrame containing query results

        Raises:
            DataSourceError: If not connected
            QueryError: If query execution fails
        """
        if not self.connection:
            raise DataSourceError(
                "Not connected to database. Call connect() first.",
                context={"datasource_id": self.config.id}
            )

        try:
            df = pd.read_sql(query, self.connection)
            return df
        except Exception as e:
            raise QueryError(
                f"Failed to execute query: {str(e)}",
                context={
                    "datasource_id": self.config.id,
                    "query": query[:QUERY_TRUNCATE_LENGTH],  # Truncate long queries
                }
            ) from e

    def get_tables(self) -> list[str]:
        """Get list of table names.

        Returns:
            List of table names in the configured schema

        Raises:
            DataSourceError: If not connected
            QueryError: If schema inspection fails
        """
        if not self.engine:
            raise DataSourceError(
                "Not connected to database. Call connect() first.",
                context={"datasource_id": self.config.id}
            )

        try:
            inspector = inspect(self.engine)
            tables = inspector.get_table_names(schema=self.config.schema)
            return tables
        except Exception as e:
            raise QueryError(
                f"Failed to get table list: {str(e)}",
                context={
                    "datasource_id": self.config.id,
                    "schema": self.config.schema,
                }
            ) from e

    def get_columns(self, table: str) -> list[dict[str, Any]]:
        """Get column metadata for a table.

        Args:
            table: Table name

        Returns:
            List of dictionaries containing column metadata.
            Each dict has keys: name, type, nullable, default

        Raises:
            DataSourceError: If not connected
            QueryError: If column inspection fails
        """
        if not self.engine:
            raise DataSourceError(
                "Not connected to database. Call connect() first.",
                context={"datasource_id": self.config.id}
            )

        try:
            inspector = inspect(self.engine)
            columns = inspector.get_columns(table, schema=self.config.schema)

            # Format column metadata
            result = []
            for col in columns:
                result.append({
                    "name": col["name"],
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": col.get("default"),
                })

            return result
        except Exception as e:
            raise QueryError(
                f"Failed to get columns for table '{table}': {str(e)}",
                context={
                    "datasource_id": self.config.id,
                    "schema": self.config.schema,
                    "table": table,
                }
            ) from e
