import sqlite3
import pytest
from app.connectors.sql_connector import SQLConnector


@pytest.fixture
def test_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)")
    conn.execute("INSERT INTO products VALUES (1, 'Widget', 9.99)")
    conn.execute("INSERT INTO products VALUES (2, 'Gadget', 19.99)")
    conn.execute("INSERT INTO products VALUES (3, 'Doohickey', 4.99)")
    conn.commit()
    conn.close()
    return db_path


class TestSQLConnector:
    def test_test_connection_sqlite(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        assert conn.test_connection() is True

    def test_test_connection_bad_path(self):
        conn = SQLConnector({"type": "sqlite", "database": "/nonexistent/path.db"})
        assert conn.test_connection() is False

    def test_discover_schema(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        cols = conn.discover_schema("products")
        names = [c.name for c in cols]
        assert "id" in names
        assert "name" in names
        assert "price" in names
        conn.close()

    def test_query_all(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products")
        assert len(rows) == 3
        assert rows[0]["name"] == "Widget"
        conn.close()

    def test_query_with_columns(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products", columns=["name", "price"])
        assert set(rows[0].keys()) == {"name", "price"}
        conn.close()

    def test_query_with_filter(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products", filters=[{"field": "price", "operator": ">", "value": "10"}])
        assert len(rows) == 1
        assert rows[0]["name"] == "Gadget"
        conn.close()

    def test_query_with_limit(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products", limit=2)
        assert len(rows) == 2
        conn.close()

    def test_query_with_eq_filter(self, test_db):
        conn = SQLConnector({"type": "sqlite", "database": test_db})
        rows = conn.query("products", filters=[{"field": "name", "operator": "=", "value": "Widget"}])
        assert len(rows) == 1
        assert rows[0]["price"] == 9.99
        conn.close()
