import os
import pytest
import csv
from app.connectors.csv_connector import CSVConnector
from app.connectors.base import ColumnDef


@pytest.fixture
def csv_file(tmp_path):
    path = str(tmp_path / "sales.csv")
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["order_id", "product", "amount", "date"])
        writer.writerow(["1", "Widget", "99.5", "2024-01-15"])
        writer.writerow(["2", "Gadget", "149.0", "2024-01-16"])
        writer.writerow(["3", "Widget", "99.5", "2024-01-17"])
    return path


@pytest.fixture
def csv_connector(tmp_path, csv_file):
    db_path = str(tmp_path / "imported.db")
    return CSVConnector({"storage_path": str(tmp_path), "database": db_path})


class TestCSVConnector:
    def test_ingest_csv(self, csv_connector, csv_file):
        cols = csv_connector.ingest(csv_file, "sales")
        names = [c.name for c in cols]
        assert "order_id" in names
        assert "amount" in names
        assert len(cols) == 4

    def test_query_after_ingest(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        rows = csv_connector.query("sales")
        assert len(rows) == 3
        assert rows[0]["product"] == "Widget"

    def test_query_with_columns(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        rows = csv_connector.query("sales", columns=["product", "amount"])
        assert set(rows[0].keys()) == {"product", "amount"}

    def test_query_with_filter(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        rows = csv_connector.query("sales", filters=[{"field": "product", "operator": "=", "value": "Widget"}])
        assert len(rows) == 2

    def test_query_with_limit(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        rows = csv_connector.query("sales", limit=1)
        assert len(rows) == 1

    def test_discover_schema_after_ingest(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        cols = csv_connector.discover_schema("sales")
        assert len(cols) == 4

    def test_test_connection(self, csv_connector, csv_file):
        csv_connector.ingest(csv_file, "sales")
        assert csv_connector.test_connection() is True

    def test_test_connection_no_db(self, tmp_path):
        conn = CSVConnector({"storage_path": str(tmp_path), "database": str(tmp_path / "nonexistent.db")})
        assert conn.test_connection() is False
