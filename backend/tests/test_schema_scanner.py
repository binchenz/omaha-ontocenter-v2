import pytest
import tempfile
import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from app.services.schema_scanner import SchemaScanner, TableSummary


@pytest.fixture
def test_db_url():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE t_order (
                id INTEGER PRIMARY KEY,
                customer_id INTEGER,
                total_amount REAL,
                status TEXT,
                created_at TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO t_order VALUES
            (1, 101, 299.00, 'pending', '2024-01-15'),
            (2, 102, 1580.50, 'shipped', '2024-02-20'),
            (3, 101, 45.00, 'delivered', '2024-03-10'),
            (4, 103, 890.00, 'cancelled', '2024-04-05'),
            (5, 102, 320.00, 'pending', '2024-05-01')
        """))
        conn.execute(text("""
            CREATE TABLE t_customer (
                id INTEGER PRIMARY KEY,
                name TEXT,
                phone TEXT,
                region TEXT
            )
        """))
        conn.execute(text("""
            INSERT INTO t_customer VALUES
            (101, 'Alice', '13800001111', 'East'),
            (102, 'Bob', '13900002222', 'West'),
            (103, 'Charlie', '13700003333', 'East')
        """))
        conn.execute(text("""
            CREATE TABLE django_migrations (
                id INTEGER PRIMARY KEY,
                app TEXT,
                name TEXT
            )
        """))
        conn.commit()
    yield engine.url
    os.unlink(path)


def test_list_tables(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    tables = scanner.list_tables()
    assert "t_order" in tables
    assert "t_customer" in tables
    assert "django_migrations" in tables


def test_scan_table_columns(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    summary = scanner.scan_table("t_order")
    assert isinstance(summary, TableSummary)
    assert summary.name == "t_order"
    col_names = [c["name"] for c in summary.columns]
    assert "id" in col_names
    assert "total_amount" in col_names
    assert "status" in col_names


def test_scan_table_row_count(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    summary = scanner.scan_table("t_order")
    assert summary.row_count == 5


def test_scan_table_sample_values(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    summary = scanner.scan_table("t_order")
    assert "status" in summary.sample_values
    status_values = summary.sample_values["status"]
    assert "pending" in status_values
    assert "shipped" in status_values


def test_scan_all(test_db_url):
    scanner = SchemaScanner(str(test_db_url))
    summaries = scanner.scan_all()
    assert len(summaries) == 3
    names = {s.name for s in summaries}
    assert names == {"t_order", "t_customer", "django_migrations"}


def test_scan_empty_table(test_db_url):
    engine = create_engine(str(test_db_url))
    with engine.connect() as conn:
        conn.execute(text("CREATE TABLE empty_table (id INTEGER PRIMARY KEY)"))
        conn.commit()
    scanner = SchemaScanner(str(test_db_url))
    summary = scanner.scan_table("empty_table")
    assert summary.row_count == 0
    assert summary.sample_values == {"id": []}
