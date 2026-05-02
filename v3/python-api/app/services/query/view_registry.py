"""Auto-register Delta tables as DuckDB views, with tenant-scoped view names."""
import os
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.datasource import Dataset
from app.services.query.duckdb_service import duckdb_service


def _safe_view_name(tenant_id: str, table_name: str) -> str:
    """Compose a view name that won't collide across tenants."""
    safe_tenant = re.sub(r"[^A-Za-z0-9_]", "_", tenant_id)
    safe_table = re.sub(r"[^A-Za-z0-9_\u4e00-\u9fff]", "_", table_name)
    return f"t_{safe_tenant}__{safe_table}"


async def ensure_view_registered(db: AsyncSession, table_name: str, tenant_id: str = "default") -> str:
    """Register a Delta table as DuckDB view for a given tenant.

    Returns the tenant-scoped view name that callers must use in SQL.
    The view is keyed by (tenant_id, table_name) so two tenants with the
    same table name never overwrite each other.
    """
    view_name = _safe_view_name(tenant_id, table_name)

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

    duckdb_service.register_delta(view_name, dataset.delta_path)
    return view_name
