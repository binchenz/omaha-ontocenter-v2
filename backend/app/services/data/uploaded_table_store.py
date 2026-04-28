

"""
Persistent storage for DataFrames uploaded during a chat session.

Pickle-based, scoped by (project_id, session_id, table_name). Lives at
backend/data/uploads/{project_id}/{session_id}/_tables/{table_name}.pkl
so it survives across requests and process restarts.
"""
from pathlib import Path
import pandas as pd

_BASE = Path("data/uploads")

def _table_dir(project_id: int, session_id: int) -> Path:
    return (_BASE / str(project_id) / str(session_id) / "_tables").resolve()

def _table_path(project_id: int, session_id: int, table_name: str) -> Path:
    safe_name = Path(table_name).name
    return _table_dir(project_id, session_id) / f"{safe_name}.pkl"

class UploadedTableStore:
    @staticmethod
    def save(project_id: int, session_id: int, table_name: str, df: pd.DataFrame) -> None:
        d = _table_dir(project_id, session_id)
        d.mkdir(parents=True, exist_ok=True)
        df.to_pickle(_table_path(project_id, session_id, table_name))

    @staticmethod
    def load(project_id: int, session_id: int, table_name: str) -> pd.DataFrame | None:
        p = _table_path(project_id, session_id, table_name)
        return pd.read_pickle(p) if p.exists() else None

    @staticmethod
    def load_all(project_id: int, session_id: int) -> dict[str, pd.DataFrame]:
        d = _table_dir(project_id, session_id)
        if not d.exists():
            return {}
        return {p.stem: pd.read_pickle(p) for p in d.glob("*.pkl")}

    @staticmethod
    def replace_all(project_id: int, session_id: int, tables: dict[str, pd.DataFrame]) -> None:
        d = _table_dir(project_id, session_id)
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("*.pkl"):
            old.unlink()
        for name, df in tables.items():
            df.to_pickle(_table_path(project_id, session_id, name))
