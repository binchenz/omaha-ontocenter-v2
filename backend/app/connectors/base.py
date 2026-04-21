from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ColumnDef:
    name: str
    type: str
    nullable: bool = True
    description: str = ""


class BaseConnector(ABC):
    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def test_connection(self) -> bool: ...

    @abstractmethod
    def discover_schema(self, source: str) -> list[ColumnDef]: ...

    @abstractmethod
    def query(
        self,
        source: str,
        columns: list[str] | None = None,
        filters: list[dict] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def close(self) -> None:
        pass
