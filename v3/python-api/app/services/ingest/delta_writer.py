import os
import pandas as pd
from deltalake import write_deltalake, DeltaTable
from app.config import settings


def sync_to_delta(df: pd.DataFrame, table_name: str, dataset_id: str) -> str:
    """Write a DataFrame to a Delta table. Returns delta path."""
    delta_path = _delta_path(table_name, dataset_id)
    # schema_mode="overwrite" permits schema evolution when the same dataset_id
    # is reused across ingests with differently-shaped CSVs (FileConnector always
    # names the table "data", so any re-upload with different columns previously
    # raised SchemaMismatchError).
    write_deltalake(delta_path, df, mode="overwrite", schema_mode="overwrite")
    return delta_path


def read_delta_snapshot(table_name: str, dataset_id: str, version: int | None = None) -> pd.DataFrame:
    """Read a Delta table snapshot into DataFrame."""
    delta_path = _delta_path(table_name, dataset_id)
    dt = DeltaTable(delta_path)
    if version is not None:
        dt.load_as_version(version)
    return dt.to_pandas()


def get_delta_metadata(table_name: str, dataset_id: str) -> dict:
    """Return version history and metadata for a Delta table."""
    delta_path = _delta_path(table_name, dataset_id)
    dt = DeltaTable(delta_path)
    return {
        "version": dt.version(),
        "files": len(dt.files()),
        "history": [{"version": h["version"], "timestamp": str(h["timestamp"]), "operation": h.get("operation", "WRITE")}
                     for h in dt.history()],
    }


def _delta_path(table_name: str, dataset_id: str) -> str:
    base = settings.delta_storage
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, f"{dataset_id}_{table_name}")
