"""Abstract base class for database connectors."""

from abc import ABC, abstractmethod
from typing import Any
import pandas as pd


class BaseConnector(ABC):
    """Abstract base class for database connectors."""

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame."""
        pass

    @abstractmethod
    def get_tables(self) -> list[str]:
        """Get list of table names."""
        pass

    @abstractmethod
    def get_columns(self, table: str) -> list[dict[str, Any]]:
        """Get column metadata for a table."""
        pass

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
