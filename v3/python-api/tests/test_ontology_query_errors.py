"""Verify DuckDB errors map to 4xx, not 5xx, on /ontology/{id}/query.

When a tool targets a table whose Delta path is missing (e.g. orphaned ontology
after data cleanup), DuckDB raises CatalogException. The endpoint must translate
that into a 4xx with an actionable message so the LLM can self-recover instead
of retrying a 500 blindly.
"""
from urllib.parse import quote

from httpx import ASGITransport, AsyncClient

from app.main import app


ORPHAN_YAML = """name: Orphan404 Test
slug: orphan-404-test
objects:
  - name: Ghost
    slug: ghost
    table_name: nonexistent_table_xyz_999
    properties:
      - name: id
        source_column: id
        semantic_type: id
      - name: value
        source_column: value
        semantic_type: text
"""


class TestOntologyQueryErrors:
    async def test_missing_table_returns_404(self):
        """Querying an ontology whose underlying table was never ingested must 404."""
        tenant = "tenant_orphan_404"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            # Create ontology — the table `nonexistent_table_xyz_999` is NOT ingested.
            r = await c.post(
                f"/ontology?tenant_id={tenant}&yaml_source=" + quote(ORPHAN_YAML)
            )
            assert r.status_code == 200, r.text
            oid = r.json()["id"]

            try:
                # Query the missing table
                r = await c.post(
                    f"/ontology/{oid}/query?tenant_id={tenant}",
                    json={"operation": "search", "object": "ghost", "limit": 5},
                )
                # Must be 4xx, not 5xx
                assert 400 <= r.status_code < 500, (
                    f"expected 4xx, got {r.status_code}: {r.text}"
                )
                # Specifically 404 for missing-table
                assert r.status_code == 404, (
                    f"expected 404 for missing table, got {r.status_code}: {r.text}"
                )
                detail = r.json()["detail"]
                assert (
                    "不存在" in detail
                    or "does not exist" in detail.lower()
                    or "not found" in detail.lower()
                ), f"detail should mention missing: {detail}"
            finally:
                await c.delete(f"/ontology/{oid}?tenant_id={tenant}")

    async def test_missing_table_count_returns_404(self):
        """count operation against missing table must also return 404."""
        tenant = "tenant_orphan_404b"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post(
                f"/ontology?tenant_id={tenant}&yaml_source=" + quote(ORPHAN_YAML)
            )
            assert r.status_code == 200, r.text
            oid = r.json()["id"]

            try:
                r = await c.post(
                    f"/ontology/{oid}/query?tenant_id={tenant}",
                    json={"operation": "count", "object": "ghost"},
                )
                assert r.status_code == 404, (
                    f"expected 404, got {r.status_code}: {r.text}"
                )
            finally:
                await c.delete(f"/ontology/{oid}?tenant_id={tenant}")

    async def test_missing_table_aggregate_returns_404(self):
        """aggregate operation against missing table must return 404."""
        tenant = "tenant_orphan_404c"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post(
                f"/ontology?tenant_id={tenant}&yaml_source=" + quote(ORPHAN_YAML)
            )
            assert r.status_code == 200, r.text
            oid = r.json()["id"]

            try:
                r = await c.post(
                    f"/ontology/{oid}/query?tenant_id={tenant}",
                    json={
                        "operation": "aggregate",
                        "object": "ghost",
                        "measures": ["COUNT(*)"],
                    },
                )
                assert r.status_code == 404, (
                    f"expected 404, got {r.status_code}: {r.text}"
                )
            finally:
                await c.delete(f"/ontology/{oid}?tenant_id={tenant}")
