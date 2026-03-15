"""MySQL/StarRocks database connector implementation."""

from typing import Any, Optional
import pandas as pd
import pymysql
from pymysql.cursors import DictCursor

from omaha.core.config.schema import DataSourceConfig
from omaha.core.data.connectors.base import BaseConnector
from omaha.utils.exceptions import DatabaseConnectionError, DataSourceError, QueryError

# Query truncation length for error messages
QUERY_TRUNCATE_LENGTH = 200


class MySQLConnector(BaseConnector):
    """MySQL/StarRocks database connector using pymysql."""

    def __init__(self, config: DataSourceConfig):
        """Initialize with connection config.

        Args:
            config: DataSourceConfig containing connection details
        """
        self.config = config
        self.connection: Optional[pymysql.connections.Connection] = None

    def connect(self) -> None:
        """Establish database connection.

        Raises:
            DatabaseConnectionError: If connection fails
        """
        # Close existing connection if any
        if self.connection:
            self.disconnect()

        try:
            # Build connection parameters
            conn_config = self.config.connection
            self.connection = pymysql.connect(
                host=conn_config.host,
                port=conn_config.port,
                user=conn_config.user,
                password=conn_config.password.get_secret_value(),
                database=conn_config.database,
                charset="utf8mb4",
                cursorclass=DictCursor
            )

        except pymysql.Error as e:
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
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass  # Suppress exceptions during cleanup
            finally:
                self.connection = None

    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame.

        Args:
            query: SQL query string

        Returns:
            Query results as pandas DataFrame

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
            # Use cursor directly instead of pandas read_sql
            # DictCursor causes issues with pandas, so we use regular cursor
            with self.connection.cursor() as cursor:
                cursor.execute(query)

                # Fetch column names
                columns = [desc[0] for desc in cursor.description] if cursor.description else []

                # Fetch all rows
                rows = cursor.fetchall()

                # Create DataFrame
                df = pd.DataFrame(rows, columns=columns)

            return df

        except pymysql.Error as e:
            # Truncate query for error message
            truncated_query = query[:QUERY_TRUNCATE_LENGTH]
            if len(query) > QUERY_TRUNCATE_LENGTH:
                truncated_query += "..."

            raise QueryError(
                f"Query execution failed: {str(e)}",
                context={
                    "datasource_id": self.config.id,
                    "query": truncated_query,
                }
            ) from e
        except Exception as e:
            # Catch other exceptions (e.g., pandas errors)
            truncated_query = query[:QUERY_TRUNCATE_LENGTH]
            if len(query) > QUERY_TRUNCATE_LENGTH:
                truncated_query += "..."

            raise QueryError(
                f"Query execution failed: {str(e)}",
                context={
                    "datasource_id": self.config.id,
                    "query": truncated_query,
                }
            ) from e

    def get_tables(self) -> list[str]:
        """Get list of table names in the database.

        Returns:
            List of table names

        Raises:
            DataSourceError: If not connected
            QueryError: If table listing fails
        """
        if not self.connection:
            raise DataSourceError(
                "Not connected to database. Call connect() first.",
                context={"datasource_id": self.config.id}
            )

        try:
            # Use pandas to execute SHOW TABLES
            df = pd.read_sql("SHOW TABLES", self.connection)

            # Extract table names from the first column
            if not df.empty:
                return df.iloc[:, 0].tolist()
            return []

        except pymysql.Error as e:
            raise QueryError(
                f"Failed to get tables: {str(e)}",
                context={
                    "datasource_id": self.config.id,
                    "schema": self.config.schema,
                }
            ) from e
        except Exception as e:
            raise QueryError(
                f"Failed to get tables: {str(e)}",
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
            List of column metadata dictionaries with keys:
                - name: Column name
                - type: Column data type
                - nullable: Whether column allows NULL
                - default: Default value (if any)

        Raises:
            DataSourceError: If not connected
            QueryError: If column inspection fails
        """
        if not self.connection:
            raise DataSourceError(
                "Not connected to database. Call connect() first.",
                context={"datasource_id": self.config.id}
            )

        try:
            # Use cursor to execute DESCRIBE
            # Note: DictCursor returns dictionaries, not tuples
            with self.connection.cursor() as cursor:
                cursor.execute(f"DESCRIBE `{table}`")
                rows = cursor.fetchall()

                # DESCRIBE returns: Field, Type, Null, Key, Default, Extra
                columns = []
                for row in rows:
                    columns.append({
                        "name": row["Field"],
                        "type": row["Type"],
                        "nullable": row["Null"] == "YES",
                        "default": row.get("Default"),
                    })

            return columns

        except pymysql.Error as e:
            raise QueryError(
                f"Failed to get columns for table '{table}': {str(e)}",
                context={
                    "datasource_id": self.config.id,
                    "schema": self.config.schema,
                    "table": table,
                }
            ) from e
        except Exception as e:
            raise QueryError(
                f"Failed to get columns for table '{table}': {str(e)}",
                context={
                    "datasource_id": self.config.id,
                    "schema": self.config.schema,
                    "table": table,
                }
            ) from e
