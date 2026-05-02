from abc import ABC, abstractmethod


class Connector(ABC):
    """Abstract connector for all data source types."""

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def discover_tables(self) -> list[str]: ...

    @abstractmethod
    async def sample_data(self, table: str, rows: int = 1000) -> list[dict]: ...

    @abstractmethod
    async def sync_table(self, table: str, delta_path: str) -> int:
        """Sync entire table to Delta Lake. Returns row count."""
        ...

    @abstractmethod
    async def close(self) -> None: ...
