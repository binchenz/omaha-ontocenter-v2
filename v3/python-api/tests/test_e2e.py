"""Comprehensive end-to-end tests for the OntoCenter v3 Python API."""
import tempfile, sqlite3, os, json
from urllib.parse import quote
from httpx import ASGITransport, AsyncClient
from app.main import app


YAML_ONTOLOGY = """name: Test E2E
slug: test-e2e
objects:
  - name: Order
    slug: order
    table_name: orders
    properties:
      - name: id
        source_column: id
        semantic_type: id
      - name: amount
        source_column: amount
        semantic_type: currency
        unit: CNY
      - name: status
        source_column: status
        semantic_type: enum
  - name: Customer
    slug: customer
    table_name: customers
    properties:
      - name: id
        source_column: id
        semantic_type: id
      - name: name
        source_column: name
        semantic_type: text
      - name: region
        source_column: region
        semantic_type: enum
links:
  - name: order_customer
    from_object: order
    to_object: customer
    from_column: customer_id
    to_column: id
functions:
  - name: growth_rate
    handler: app.functions.stats.growth_rate
    description: Calculate growth rate
    caching_ttl: '1h'"""


async def _setup_db():
    fd, dbpath = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(dbpath)
    conn.execute("CREATE TABLE orders (id INTEGER, customer_id INTEGER, amount REAL, status TEXT)")
    conn.execute("CREATE TABLE customers (id INTEGER, name TEXT, region TEXT)")
    conn.execute("INSERT INTO orders VALUES (1, 1, 52000, 'delayed'), (2, 2, 31000, 'shipped'), (3, 1, 18000, 'pending')")
    conn.execute("INSERT INTO customers VALUES (1, '深圳科技', '华南'), (2, '广州贸易', '华南')")
    conn.commit(); conn.close()
    return dbpath


class TestE2EFullFlow:
    async def test_01_health(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/health")
            assert r.status_code == 200
            assert r.json()["status"] == "ok"

    async def test_02_discover(self):
        dbpath = await _setup_db()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post("/ingest/discover", data={"type": "sqlite", "path": dbpath})
                assert r.status_code == 200
                data = r.json()
                assert "orders" in data["tables"] or "customers" in data["tables"]
        finally:
            os.unlink(dbpath)

    async def test_03_ingest(self):
        dbpath = await _setup_db()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                r = await c.post("/ingest", data={"type": "sqlite", "path": dbpath})
                assert r.status_code == 200
                data = r.json()
                assert data["rows_count"] == 3
                assert data["status"] == "ready"
                assert len(data["columns"]) > 0
                assert data["columns"][0]["semantic_type"] in ("id", "number", "text")
        finally:
            os.unlink(dbpath)

    async def test_04_create_ontology_and_query(self):
        dbpath = await _setup_db()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                # Create ontology
                r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
                assert r.status_code == 200
                ont = r.json()
                oid = ont["id"]

                # List ontologies
                r = await c.get("/ontology")
                assert r.status_code == 200
                assert any(o["id"] == oid for o in r.json())

                # Get schema
                r = await c.get(f"/ontology/{oid}/schema")
                assert r.status_code == 200
                s = r.json()
                assert len(s["objects"]) == 2
                assert len(s["links"]) == 1

                # Export YAML
                r = await c.get(f"/ontology/{oid}/yaml")
                assert r.status_code == 200
                assert "yaml" in r.json()

                # OAG search
                r = await c.post(f"/ontology/{oid}/query", json={
                    "operation": "search", "object": "order", "limit": 5
                })
                assert r.status_code == 200
                oag = r.json()
                assert oag["object_type"] == "Order"
                assert len(oag["matched"]) > 0

                # OAG count
                r = await c.post(f"/ontology/{oid}/query", json={
                    "operation": "count", "object": "order"
                })
                assert r.status_code == 200

                # OAG aggregate
                r = await c.post(f"/ontology/{oid}/query", json={
                    "operation": "aggregate", "object": "order",
                    "measures": ["COUNT(*)"], "group_by": ["status"]
                })
                assert r.status_code == 200

                # MCP generate
                r = await c.post(f"/mcp/generate/{oid}")
                assert r.status_code == 200
                mcp = r.json()
                assert mcp["tools_count"] >= 3
                assert "search_order" in str(mcp["tools"])
                assert "skill" in mcp
                assert "skill_markdown" in mcp

                # Function call (now requires ontology_id and registered handler)
                r = await c.post(
                    f"/ontology/{oid}/function/growth_rate",
                    params={"kwargs": json.dumps({"current": 150, "previous": 100})}
                )
                assert r.status_code == 200
                fn = r.json()
                assert fn["rate"] == 0.5

        finally:
            os.unlink(dbpath)

    async def test_05_error_handling(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            # Non-existent ontology
            r = await c.get("/ontology/nonexistent/schema")
            assert r.status_code == 404

            # Missing YAML source — form-based endpoint, returns 400
            r = await c.post("/ontology", data={})
            assert r.status_code == 400

            # MCP for non-existent ontology
            r = await c.post("/mcp/generate/nonexistent")
            assert r.status_code == 404

    async def test_06_ingest_unsupported_type(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ingest", data={"type": "mongodb", "host": "localhost"})
            assert r.status_code == 400
            assert r.json()["detail"].startswith("不支持的连接类型")

    async def test_07_health_again(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/health")
            assert r.status_code == 200

    async def test_08_delete_ontology(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            # Create
            r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
            oid = r.json()["id"]
            # Delete
            r = await c.delete(f"/ontology/{oid}")
            assert r.status_code == 200
            assert r.json()["deleted"] is True
            # Verify gone
            r = await c.get(f"/ontology/{oid}/schema")
            assert r.status_code == 404

    async def test_09_skills_list(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
            oid = r.json()["id"]
            r = await c.get("/mcp/skills")
            assert r.status_code == 200
            skills = r.json()["skills"]
            assert any(s["ontology_id"] == oid for s in skills)
            await c.delete(f"/ontology/{oid}")

    async def test_10_update_ontology(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
            oid = r.json()["id"]
            new_yaml = YAML_ONTOLOGY.replace("Test E2E", "Updated Name")
            r = await c.put(f"/ontology/{oid}?yaml_source=" + quote(new_yaml))
            assert r.status_code == 200
            assert r.json()["name"] == "Updated Name"
            new_oid = r.json()["id"]
            await c.delete(f"/ontology/{new_oid}")

    async def test_11_mcp_runtime_endpoint(self):
        """Verify MCP HTTP endpoint actually responds to JSON-RPC."""
        dbpath = await _setup_db()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                # Setup
                await c.post("/ingest", data={"type": "sqlite", "path": dbpath})
                r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
                slug = "test-e2e"

                # tools/list via MCP runtime
                r = await c.post(f"/mcp/{slug}", json={
                    "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
                })
                assert r.status_code == 200
                resp = r.json()
                assert "result" in resp
                tools = resp["result"]["tools"]
                assert len(tools) > 0
                assert any(t["name"].startswith("search_") for t in tools)

                # tools/call via MCP runtime
                r = await c.post(f"/mcp/{slug}", json={
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": "search_order", "arguments": {"limit": 5}}
                })
                assert r.status_code == 200
                resp = r.json()
                assert "result" in resp

                # Unknown ontology slug
                r = await c.post("/mcp/nonexistent", json={
                    "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
                })
                assert r.status_code == 404
        finally:
            os.unlink(dbpath)
            # Cleanup ontology
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                onts = (await c.get("/ontology")).json()
                for o in onts:
                    if o["slug"] == "test-e2e":
                        await c.delete(f"/ontology/{o['id']}")

    async def test_12_datasources_list(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/datasources")
            assert r.status_code == 200
            assert isinstance(r.json(), list)
            # Each item must have datasets array
            for ds in r.json():
                assert "datasets" in ds
                assert "type" in ds

    async def test_13_datasource_delete_removes_delta(self):
        """Deleting a datasource should remove its Delta files from disk."""
        import tempfile, sqlite3
        fd, dbpath = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(dbpath)
        conn.execute("CREATE TABLE del_test (id INTEGER, val TEXT)")
        conn.execute("INSERT INTO del_test VALUES (1,'a'),(2,'b')")
        conn.commit(); conn.close()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ingest", data={"type": "sqlite", "path": dbpath})
            assert r.status_code == 200
            delta_path = r.json()["delta_path"]
            assert os.path.exists(delta_path), "Delta should exist after ingest"

            ds_list = (await c.get("/datasources")).json()
            target_ds = next((ds for ds in ds_list if any(d["table_name"] == "del_test" for d in ds["datasets"])), None)
            assert target_ds

            r = await c.delete(f"/datasources/{target_ds['id']}")
            assert r.status_code == 200
            assert r.json()["deleted"] is True
            assert not os.path.exists(delta_path), "Delta should be removed"

        os.unlink(dbpath)

    async def test_14_cleanup_orphan_deltas(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/datasources/cleanup-orphans")
            assert r.status_code == 200
            data = r.json()
            assert "removed" in data
            assert "kept" in data

    async def test_15_mcp_servers_list(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
            oid = r.json()["id"]

            r = await c.get("/mcp/servers")
            assert r.status_code == 200
            servers = r.json()["servers"]
            assert any(s["ontology_slug"] == "test-e2e" for s in servers)
            target = next(s for s in servers if s["ontology_slug"] == "test-e2e")
            assert target["endpoint"].endswith("/mcp/test-e2e")
            assert target["status"] == "running"

            await c.delete(f"/ontology/{oid}")

    async def test_16_friendly_input_errors(self):
        """Bad user input should return 400, not 500."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            # Bad YAML
            r = await c.post("/ontology?yaml_source=" + quote("invalid: yaml: [[["))
            assert r.status_code == 400
            assert "YAML" in r.json()["detail"]

    async def test_16b_rce_prevented(self):
        """Function handler must come from registered ontology, not from query param."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
            oid = r.json()["id"]
            try:
                # Cannot invoke unregistered function
                r = await c.post(
                    f"/ontology/{oid}/function/os.system",
                    params={"kwargs": json.dumps({})}
                )
                assert r.status_code == 404

                # Cannot invoke arbitrary import
                r = await c.post(
                    f"/ontology/{oid}/function/subprocess.run",
                    params={"kwargs": json.dumps({})}
                )
                assert r.status_code == 404

                # Registered function works
                r = await c.post(
                    f"/ontology/{oid}/function/growth_rate",
                    params={"kwargs": json.dumps({"current": 100, "previous": 50})}
                )
                assert r.status_code == 200
                assert r.json()["rate"] == 1.0
            finally:
                await c.delete(f"/ontology/{oid}")

    async def test_16c_yaml_rce_prevented(self):
        """YAML cannot register malicious handler paths like os.system."""
        malicious_yaml = """name: Evil
slug: evil-test
objects:
  - name: Dummy
    slug: dummy
    table_name: dummies
    properties:
      - name: id
        source_column: id
        semantic_type: id
functions:
  - name: pwn
    handler: os.system
    description: RCE attempt"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ontology?yaml_source=" + quote(malicious_yaml))
            assert r.status_code == 400
            assert "handler" in r.json()["detail"]

    async def test_17_sql_injection_blocked(self):
        """Malicious measures / group_by / filters must be rejected as ValueError."""
        dbpath = await _setup_db()
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                await c.post("/ingest", data={"type": "sqlite", "path": dbpath})
                r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
                oid = r.json()["id"]

                # Malicious measure
                r = await c.post(f"/ontology/{oid}/query", json={
                    "operation": "aggregate", "object": "order",
                    "measures": ["1; DROP VIEW orders; --"],
                })
                assert r.status_code == 400

                # Malicious group_by
                r = await c.post(f"/ontology/{oid}/query", json={
                    "operation": "aggregate", "object": "order",
                    "measures": ["COUNT(*)"], "group_by": ["status; DELETE FROM x"],
                })
                assert r.status_code == 400

                # Malicious filter column
                r = await c.post(f"/ontology/{oid}/query", json={
                    "operation": "search", "object": "order",
                    "filters": {"id OR 1=1": "x"},
                })
                assert r.status_code == 400

                # Non-whitelisted aggregate function
                r = await c.post(f"/ontology/{oid}/query", json={
                    "operation": "aggregate", "object": "order",
                    "measures": ["EXPLOIT(amount)"],
                })
                assert r.status_code == 400

                await c.delete(f"/ontology/{oid}")
        finally:
            os.unlink(dbpath)

    async def test_18_tenant_isolation(self):
        """One tenant cannot read another tenant's ontology by id."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ontology?tenant_id=tenant_a&yaml_source=" + quote(YAML_ONTOLOGY))
            oid = r.json()["id"]
            try:
                r = await c.get(f"/ontology/{oid}/schema?tenant_id=tenant_b")
                assert r.status_code == 404
                r = await c.delete(f"/ontology/{oid}?tenant_id=tenant_b")
                assert r.status_code == 404
            finally:
                await c.delete(f"/ontology/{oid}?tenant_id=tenant_a")

    async def test_19_put_preserves_id(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
            oid = r.json()["id"]
            new_yaml = YAML_ONTOLOGY.replace("Test E2E", "Renamed")
            r = await c.put(f"/ontology/{oid}?yaml_source=" + quote(new_yaml))
            assert r.status_code == 200
            assert r.json()["id"] == oid
            assert r.json()["name"] == "Renamed"
            await c.delete(f"/ontology/{oid}")

    async def test_20_function_cache_key_includes_kwargs(self):
        import json as json_mod
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ontology?yaml_source=" + quote(YAML_ONTOLOGY))
            oid = r.json()["id"]
            try:
                r1 = await c.post(
                    f"/ontology/{oid}/function/growth_rate",
                    params={"kwargs": json_mod.dumps({"current": 100, "previous": 80})}
                )
                r2 = await c.post(
                    f"/ontology/{oid}/function/growth_rate",
                    params={"kwargs": json_mod.dumps({"current": 200, "previous": 100})}
                )
                assert r1.status_code == 200
                assert r2.status_code == 200
                assert r1.json()["rate"] != r2.json()["rate"]
            finally:
                await c.delete(f"/ontology/{oid}")

    async def test_21_csv_ingest_works(self):
        """FileConnector previously had bug where __init__ didn't read config[path]."""
        import tempfile
        fd, csv_path = tempfile.mkstemp(suffix=".csv")
        os.write(fd, b"id,name,price\n1,iPhone,8999\n2,iPad,5499\n")
        os.close(fd)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            with open(csv_path, "rb") as f:
                r = await c.post("/ingest", data={"type": "csv"}, files={"file": ("test.csv", f, "text/csv")})
            assert r.status_code == 200
            assert r.json()["rows_count"] == 2

        os.unlink(csv_path)

    async def test_22_ingest_reuses_dataset(self):
        """Repeated ingest of same (tenant, table) should reuse dataset_id, not create orphans."""
        import tempfile
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            fd, db1 = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            import sqlite3
            conn = sqlite3.connect(db1)
            conn.execute("CREATE TABLE reuse_test (id INTEGER, v TEXT)")
            conn.execute("INSERT INTO reuse_test VALUES (1, 'a')")
            conn.commit(); conn.close()

            r1 = await c.post("/ingest", data={"type": "sqlite", "path": db1})
            id1 = r1.json()["dataset_id"]
            path1 = r1.json()["delta_path"]

            # Update source and re-ingest — should reuse the same dataset_id
            conn = sqlite3.connect(db1)
            conn.execute("INSERT INTO reuse_test VALUES (2, 'b')")
            conn.commit(); conn.close()

            r2 = await c.post("/ingest", data={"type": "sqlite", "path": db1})
            id2 = r2.json()["dataset_id"]
            path2 = r2.json()["delta_path"]

            assert id1 == id2, "dataset_id should be reused"
            assert path1 == path2, "delta_path should be stable"
            assert r2.json()["rows_count"] == 2

            os.unlink(db1)

    async def test_23_datasource_delete_tenant_scoped(self):
        """DELETE /datasources/{id} must enforce tenant isolation."""
        import tempfile, sqlite3
        fd, dbpath = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(dbpath)
        conn.execute("CREATE TABLE iso_test (id INTEGER)")
        conn.execute("INSERT INTO iso_test VALUES (1)")
        conn.commit(); conn.close()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ingest", data={"type": "sqlite", "path": dbpath, "tenant_id": "tenant_a"})
            assert r.status_code == 200

            ds_list = (await c.get("/datasources?tenant_id=tenant_a")).json()
            target = next((d for d in ds_list if any(ds["table_name"] == "iso_test" for ds in d["datasets"])), None)
            assert target

            r = await c.delete(f"/datasources/{target['id']}?tenant_id=tenant_b")
            assert r.status_code == 404

            r = await c.delete(f"/datasources/{target['id']}?tenant_id=tenant_a")
            assert r.status_code == 200

        os.unlink(dbpath)

    async def test_24_ingest_tenant_forwarded(self):
        """Ingest with tenant_id must make data queryable via ontology in that tenant."""
        import tempfile, sqlite3
        fd, dbpath = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(dbpath)
        conn.execute("CREATE TABLE tenant_query (id INTEGER, amount REAL)")
        conn.execute("INSERT INTO tenant_query VALUES (1, 100.0), (2, 200.0)")
        conn.commit(); conn.close()

        yaml_src = """name: TenantQ
slug: tenant-q-test
objects:
  - name: Row
    slug: row
    table_name: tenant_query
    properties:
      - name: id
        source_column: id
        semantic_type: id
      - name: amount
        source_column: amount
        semantic_type: currency
        unit: CNY"""

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/ingest", data={"type": "sqlite", "path": dbpath, "tenant_id": "tenant_c"})
            assert r.status_code == 200

            r = await c.post("/ontology?tenant_id=tenant_c", json={"yaml_source": yaml_src})
            assert r.status_code == 200
            oid = r.json()["id"]

            r = await c.post(
                f"/ontology/{oid}/query?tenant_id=tenant_c",
                json={"operation": "search", "object": "row", "limit": 10}
            )
            assert r.status_code == 200
            assert len(r.json()["matched"]) == 2

            # Tenant D cannot access
            r = await c.post(
                f"/ontology/{oid}/query?tenant_id=tenant_d",
                json={"operation": "search", "object": "row", "limit": 10}
            )
            assert r.status_code == 404

            await c.delete(f"/ontology/{oid}?tenant_id=tenant_c")
        os.unlink(dbpath)

    async def test_25_crypto_roundtrip(self):
        from app.core.crypto import encrypt_str, decrypt_str, encrypt_config
        assert decrypt_str(encrypt_str("hunter2")) == "hunter2"
        cfg = encrypt_config({"user": "admin", "password": "s3cret!@#"})
        assert cfg["user"] == "admin"
        assert cfg["password"] != "s3cret!@#"
        assert decrypt_str(cfg["password"]) == "s3cret!@#"

    async def test_26_internal_auth_blocks_when_secret_set(self):
        """Setting INTERNAL_API_SECRET should reject requests without the matching header.

        H1 fix: when the operator configures a shared secret (production
        posture), every endpoint except /health must demand the
        X-Internal-Auth header. We mutate the live settings object rather
        than spinning up a second app to verify the *deployed* middleware,
        and restore the prior value in `finally` so subsequent tests run
        without auth (matching their unset-secret expectation).
        """
        from app.config import settings
        original = settings.internal_api_secret
        settings.internal_api_secret = "test-secret-xyz"
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                # No header → 401
                r = await c.get("/ontology?tenant_id=anything")
                assert r.status_code == 401, r.text
                assert r.json()["detail"] == "Unauthorized"

                # Wrong header → 401
                r = await c.get(
                    "/ontology?tenant_id=anything",
                    headers={"X-Internal-Auth": "wrong"},
                )
                assert r.status_code == 401

                # Correct header → 200
                r = await c.get(
                    "/ontology?tenant_id=anything",
                    headers={"X-Internal-Auth": "test-secret-xyz"},
                )
                assert r.status_code == 200

                # /health must always be reachable for k8s probes,
                # even with no auth header.
                r = await c.get("/health")
                assert r.status_code == 200
        finally:
            settings.internal_api_secret = original

    async def test_27_internal_auth_disabled_when_secret_empty(self):
        """Empty INTERNAL_API_SECRET must keep the API open (dev convenience)."""
        from app.config import settings
        original = settings.internal_api_secret
        settings.internal_api_secret = ""
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
                # No header but secret unset → request goes through
                r = await c.get("/ontology?tenant_id=anything")
                assert r.status_code == 200
        finally:
            settings.internal_api_secret = original
