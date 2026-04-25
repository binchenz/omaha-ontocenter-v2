from dataclasses import dataclass, field
from sqlalchemy import create_engine, inspect, text


@dataclass
class TableSummary:
    name: str
    row_count: int
    columns: list[dict]
    sample_values: dict[str, list[str]] = field(default_factory=dict)


class SchemaScanner:
    def __init__(self, connection_url: str):
        self.engine = create_engine(connection_url)

    def list_tables(self) -> list[str]:
        inspector = inspect(self.engine)
        return inspector.get_table_names()

    def scan_table(self, table_name: str) -> TableSummary:
        inspector = inspect(self.engine)
        columns = [
            {"name": c["name"], "type": str(c["type"]), "nullable": c.get("nullable", True)}
            for c in inspector.get_columns(table_name)
        ]
        row_count = self._get_row_count(table_name)
        samples = self._sample_values(table_name, columns)
        return TableSummary(
            name=table_name, row_count=row_count,
            columns=columns, sample_values=samples,
        )

    def scan_all(self) -> list[TableSummary]:
        return [self.scan_table(t) for t in self.list_tables()]

    def _get_row_count(self, table_name: str) -> int:
        with self.engine.connect() as conn:
            result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
            return result.scalar() or 0

    def _sample_values(self, table_name: str, columns: list[dict], limit: int = 500) -> dict[str, list[str]]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                text(f'SELECT * FROM "{table_name}" LIMIT :lim'),
                {"lim": limit},
            ).mappings().all()
        samples = {}
        for col in columns:
            col_name = col["name"]
            values = list(set(
                str(row[col_name]) for row in rows if row.get(col_name) is not None
            ))
            samples[col_name] = sorted(values)[:20]
        return samples

    def close(self):
        self.engine.dispose()
