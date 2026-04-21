import os
import pandas as pd
from sqlalchemy import create_engine
from app.connectors.base import BaseConnector, ColumnDef
from app.connectors.sql_connector import SQLConnector


class CSVConnector(BaseConnector):
    def _db_path(self) -> str:
        return self.config.get("database", "")

    def _sql(self) -> SQLConnector:
        if not hasattr(self, "_sql_instance"):
            self._sql_instance = SQLConnector({"type": "sqlite", "database": self._db_path()})
        return self._sql_instance

    def test_connection(self) -> bool:
        return os.path.exists(self._db_path())

    def discover_schema(self, source: str) -> list[ColumnDef]:
        return self._sql().discover_schema(source)

    def query(self, source, columns=None, filters=None, limit=None):
        return self._sql().query(source, columns, filters, limit)

    def ingest(self, file_path: str, table_name: str) -> list[ColumnDef]:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path)
        else:
            df = pd.read_csv(file_path)

        engine = create_engine(f"sqlite:///{self._db_path()}")
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        engine.dispose()

        return self._infer_schema(df)

    @staticmethod
    def _infer_schema(df: pd.DataFrame) -> list[ColumnDef]:
        type_map = {"int64": "integer", "float64": "decimal", "object": "string", "bool": "boolean"}
        return [
            ColumnDef(
                name=col,
                type=type_map.get(str(df[col].dtype), "string"),
                nullable=bool(df[col].isnull().any()),
            )
            for col in df.columns
        ]
