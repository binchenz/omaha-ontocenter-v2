import sqlite3
from app.connectors.base import Connector


class SQLiteConnector(Connector):
    def __init__(self, config: dict):
        super().__init__(config)
        self.conn: sqlite3.Connection | None = None

    async def connect(self) -> None:
        self.conn = sqlite3.connect(self.config["path"])
        self.conn.row_factory = sqlite3.Row

    async def discover_tables(self) -> list[str]:
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        return [row[0] for row in cursor.fetchall()]

    async def sample_data(self, table: str, rows: int = 1000) -> list[dict]:
        if rows > 0:
            cursor = self.conn.execute(f'SELECT * FROM "{table}" LIMIT ?', (rows,))
        else:
            cursor = self.conn.execute(f'SELECT * FROM "{table}"')
        return [dict(row) for row in cursor.fetchall()]

    async def sync_table(self, table: str, delta_path: str) -> int:
        import pandas as pd
        df = pd.read_sql_query(f'SELECT * FROM "{table}"', self.conn)
        from deltalake import write_deltalake
        write_deltalake(delta_path, df, mode="overwrite")
        return len(df)

    async def close(self) -> None:
        if self.conn:
            self.conn.close()
