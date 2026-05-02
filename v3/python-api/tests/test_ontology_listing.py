"""Verify /ontology and /datasources list endpoints respect ?limit= + ?order=.

These replaced a client-side .slice(-10) so we don't transfer MBs of JSON
just to throw away 99% of it on tenants with thousands of items.
"""
from urllib.parse import quote

from httpx import ASGITransport, AsyncClient

from app.main import app


def _make_yaml(i: int) -> str:
    return f"""name: LimitTest{i}
slug: limit-test-{i}
objects:
  - name: Row
    slug: row
    table_name: t{i}
    properties:
      - name: id
        source_column: id
        semantic_type: id
"""


class TestOntologyListing:
    async def test_ontology_list_respects_limit(self):
        tenant = "test_limit_list"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            created_ids = []
            try:
                for i in range(3):
                    r = await c.post(
                        f"/ontology?tenant_id={tenant}&yaml_source=" + quote(_make_yaml(i))
                    )
                    assert r.status_code == 200, r.text
                    created_ids.append(r.json()["id"])

                r = await c.get(f"/ontology?tenant_id={tenant}&limit=2")
                assert r.status_code == 200
                items = r.json()
                assert len(items) == 2
            finally:
                for oid in created_ids:
                    await c.delete(f"/ontology/{oid}?tenant_id={tenant}")

    async def test_ontology_list_order_desc_default(self):
        """Default order is desc — most-recently-updated first."""
        tenant = "test_limit_order"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            created_ids = []
            try:
                for i in range(3):
                    r = await c.post(
                        f"/ontology?tenant_id={tenant}&yaml_source=" + quote(_make_yaml(i))
                    )
                    assert r.status_code == 200, r.text
                    created_ids.append(r.json()["id"])

                # desc (default): most-recent first — last created comes first
                r = await c.get(f"/ontology?tenant_id={tenant}")
                assert r.status_code == 200
                desc_ids = [o["id"] for o in r.json()]
                assert desc_ids[0] == created_ids[-1]

                # asc: oldest first
                r = await c.get(f"/ontology?tenant_id={tenant}&order=asc")
                assert r.status_code == 200
                asc_ids = [o["id"] for o in r.json()]
                assert asc_ids[0] == created_ids[0]
            finally:
                for oid in created_ids:
                    await c.delete(f"/ontology/{oid}?tenant_id={tenant}")

    async def test_ontology_list_limit_bounds(self):
        """limit must be in [1, 500] — FastAPI returns 422 outside that."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/ontology?limit=0")
            assert r.status_code == 422
            r = await c.get("/ontology?limit=501")
            assert r.status_code == 422

    async def test_datasources_list_respects_limit(self):
        """?limit= clamps datasource list. Validates param parsing even with no data."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/datasources?tenant_id=empty_ds_tenant&limit=5")
            assert r.status_code == 200
            assert isinstance(r.json(), list)

    async def test_datasources_list_limit_bounds(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/datasources?limit=0")
            assert r.status_code == 422
            r = await c.get("/datasources?limit=501")
            assert r.status_code == 422

    async def test_datasources_list_invalid_order(self):
        """order= only accepts 'asc' or 'desc'."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/datasources?order=random")
            assert r.status_code == 422
