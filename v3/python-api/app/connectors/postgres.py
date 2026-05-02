import pandas as pd
from urllib.parse import quote_plus
from sqlalchemy import create_engine, text
from app.connectors.base import Connector


class PostgresConnector(Connector):
    def __init__(self, config: dict):
        super().__init__(config)
        self.engine = None

    def _build_url(self) -> str:
        user = quote_plus(str(self.config["user"]))
        password = quote_plus(str(self.config["password"]))
        return (
            f"postgresql://{user}:{password}"
            f"@{self.config['host']}:{self.config.get('port', 5432)}/{self.config['database']}"
        )

    async def connect(self) -> None:
        self.engine = create_engine(self._build_url())

    async def discover_tables(self) -> list[str]:
        with self.engine.connect() as conn:
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            return [row[0] for row in result]

    async def sample_data(self, table: str, rows: int = 1000) -> list[dict]:
        if rows > 0:
            df = pd.read_sql_query(f'SELECT * FROM "{table}" LIMIT {rows}', self.engine)
        else:
            df = pd.read_sql_query(f'SELECT * FROM "{table}"', self.engine)
        return df.to_dict("records")

    async def sync_table(self, table: str, delta_path: str) -> int:
        df = pd.read_sql_query(f'SELECT * FROM "{table}"', self.engine)
        from deltalake import write_deltalake
        write_deltalake(delta_path, df, mode="overwrite")
        return len(df)

    async def close(self) -> None:
        if self.engine:
            self.engine.dispose()
