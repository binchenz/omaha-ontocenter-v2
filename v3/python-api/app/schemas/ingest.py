from pydantic import BaseModel, Field
from typing import Any


class ConnectionConfig(BaseModel):
    host: str = ""
    port: int = 5432
    database: str = ""
    user: str = ""
    password: str = ""
    path: str = ""  # for SQLite file path


class IngestRequest(BaseModel):
    type: str = Field(..., description="csv | excel | mysql | postgres | sqlite")
    connection: ConnectionConfig | None = None
    options: dict[str, Any] | None = None
    selected_table: str | None = Field(
        default=None,
        description="Specific table to ingest (from discover step). When None, the first discovered table is used.",
    )


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    semantic_type: str
    sample_values: list[Any]
    null_count: int
    unique_count: int


class TableDiscovery(BaseModel):
    tables: list[str]
    columns: dict[str, list[ColumnInfo]] = {}
    sample_rows: dict[str, list[dict]] = {}


class IngestResponse(BaseModel):
    dataset_id: str
    table_name: str
    rows_count: int
    columns: list[ColumnInfo]
    delta_path: str
    status: str
