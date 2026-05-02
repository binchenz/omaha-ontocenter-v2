from httpx import ASGITransport, AsyncClient
from app.main import app


async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "0.1.0"}


async def test_ingest_discover_sqlite():
    import tempfile
    import sqlite3
    import os

    # Create a temp SQLite db
    fd, dbpath = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(dbpath)
    conn.execute("CREATE TABLE test_table (id INTEGER, name TEXT, amount REAL)")
    conn.execute("INSERT INTO test_table VALUES (1, 'test', 100.5)")
    conn.commit()
    conn.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test discover
        response = await client.post("/ingest/discover", data={
            "type": "sqlite",
            "path": dbpath,
        })
        assert response.status_code == 200
        data = response.json()
        assert "test_table" in data["tables"]

        # Test ingest
        response = await client.post("/ingest", data={
            "type": "sqlite",
            "path": dbpath,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["rows_count"] == 1
        assert data["table_name"] == "test_table"
        assert data["status"] == "ready"

    os.unlink(dbpath)
