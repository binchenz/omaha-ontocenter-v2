import tempfile
import pandas as pd
from fastapi import UploadFile
from app.connectors.base import Connector


class FileConnector(Connector):
    """Handles CSV/Excel file uploads. Config is populated after file is saved."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.file_path: str = config.get("path", "")
        self.file_type: str = config.get("file_type", "csv")

    async def connect(self) -> None:
        pass

    async def discover_tables(self) -> list[str]:
        return ["data"]

    async def sample_data(self, table: str = "data", rows: int = 1000) -> list[dict]:
        df = self._read_file(rows)
        return df.to_dict("records")

    async def sync_table(self, table: str, delta_path: str) -> int:
        df = self._read_file()
        from deltalake import write_deltalake
        write_deltalake(delta_path, df, mode="overwrite")
        return len(df)

    def _read_file(self, rows: int | None = None) -> pd.DataFrame:
        nrows = rows if rows else None
        if self.file_type == "csv":
            return pd.read_csv(self.file_path, nrows=nrows)
        elif self.file_type == "excel":
            return pd.read_excel(self.file_path, nrows=nrows)
        raise ValueError(f"Unsupported file type: {self.file_type}")

    async def close(self) -> None:
        pass

    @staticmethod
    async def save_upload(file: UploadFile, dest_dir: str) -> str:
        import os
        os.makedirs(dest_dir, exist_ok=True)
        file_type = "csv" if file.filename and file.filename.endswith(".csv") else "excel"
        suffix = ".csv" if file_type == "csv" else ".xlsx"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=dest_dir) as tmp:
            content = await file.read()
            tmp.write(content)
            return tmp.name
