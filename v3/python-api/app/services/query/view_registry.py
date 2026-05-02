"""Auto-register Delta tables as DuckDB views, with tenant-scoped view names."""
import hashlib
import os
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.datasource import Dataset
from app.services.query.duckdb_service import duckdb_service

_IDENT_OK = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Process-level cache: (tenant_id, table_name, delta_path) -> view_name
# Keyed on delta_path so a re-ingest (which writes a new path) forces
# re-registration automatically.
_view_cache: dict[tuple[str, str, str], str] = {}


def safe_view_name(tenant_id: str, table_name: str) -> str:
    """Tenant-prefixed DuckDB view name.

    Tenant is hashed (sha1[:12] hex prefix) to avoid collisions between
    sanitized variants — e.g. 'a-b' and 'a_b' would both normalize to
    'a_b' if we just regex-replaced punctuation, causing cross-tenant
    view collisions. The table_name part is kept verbatim because
    callers are expected to have passed it through
    ``sql_safety.validate_identifier`` already.
    """
    if not _IDENT_OK.match(table_name):
        raise ValueError(f"Invalid table_name for view: {table_name!r}")
    tenant_hash = hashlib.sha1(tenant_id.encode("utf-8")).hexdigest()[:12]
    return f"t_{tenant_hash}__{table_name}"


def invalidate_view_cache(tenant_id: str, table_name: str) -> None:
    """Drop any cached registration for ``(tenant_id, table_name)``.

    Must be called whenever the underlying view is dropped from DuckDB
    (e.g. on ontology deletion) so the next ``ensure_view_registered``
    call re-creates it instead of trusting the stale cache.
    """
    stale = [k for k in _view_cache if k[0] == tenant_id and k[1] == table_name]
    for k in stale:
        _view_cache.pop(k, None)


async def ensure_view_registered(db: AsyncSession, table_name: str, tenant_id: str = "default") -> str:
    """Register a Delta table as DuckDB view for a given tenant.

    Returns the tenant-scoped view name that callers must use in SQL.
    The view is keyed by (tenant_id, table_name) so two tenants with the
    same table name never overwrite each other.

    A process-level cache keyed on ``(tenant_id, table_name, delta_path)``
    avoids re-issuing ``CREATE OR REPLACE VIEW`` on every query. When the
    underlying dataset is re-ingested (new delta_path), the cache key
    changes and the view is re-registered transparently.
    """
    view_name = safe_view_name(tenant_id, table_name)

    result = await db.execute(
        select(Dataset)
        .where(Dataset.table_name == table_name, Dataset.tenant_id == tenant_id)
        .order_by(Dataset.created_at.desc())
        .limit(1)
    )
    dataset = result.scalar_one_or_none()
    if not dataset or not dataset.delta_path:
        return view_name

    if not os.path.exists(dataset.delta_path):
        return view_name

    cache_key = (tenant_id, table_name, dataset.delta_path)
    if _view_cache.get(cache_key) == view_name:
        return view_name

    duckdb_service.register_delta(view_name, dataset.delta_path)
    _view_cache[cache_key] = view_name
    return view_name
