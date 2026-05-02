import threading
import duckdb


class DuckDBService:
    """Query Delta Lake tables via DuckDB in-process engine.

    A single DuckDB connection is not thread/coroutine safe. We use a lock
    around register + query pairs so concurrent requests can't stomp views.
    """

    def __init__(self):
        self.conn = duckdb.connect()
        self._lock = threading.Lock()

    def register_delta(self, name: str, delta_path: str) -> None:
        with self._lock:
            self.conn.execute(f"""
                CREATE OR REPLACE VIEW "{name}" AS
                SELECT * FROM delta_scan('{delta_path}')
            """)

    def query(self, sql: str) -> list[dict]:
        with self._lock:
            result = self.conn.execute(sql)
            columns = [desc[0] for desc in result.description]
            return [dict(zip(columns, row)) for row in result.fetchall()]

    def execute(self, sql: str) -> None:
        with self._lock:
            self.conn.execute(sql)

    def count(self, view: str, where: str | None = None) -> int:
        sql = f'SELECT COUNT(*) FROM "{view}"'
        if where:
            sql += f" WHERE {where}"
        with self._lock:
            return self.conn.execute(sql).fetchone()[0]

    def aggregate(
        self, view: str, measures: list[str], group_by: list[str] | None = None,
        where: str | None = None
    ) -> list[dict]:
        all_cols = list(group_by or []) + list(measures)
        cols = ", ".join(all_cols)
        sql = f"SELECT {cols} FROM \"{view}\""
        if where:
            sql += f" WHERE {where}"
        if group_by:
            sql += f" GROUP BY {', '.join(group_by)}"
        return self.query(sql)

    def drop_view(self, name: str) -> None:
        with self._lock:
            safe = name.replace('"', '""')
            self.conn.execute(f'DROP VIEW IF EXISTS "{safe}"')

    def close(self) -> None:
        self.conn.close()


duckdb_service = DuckDBService()
