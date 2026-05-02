import shutil
from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.api.deps import Pagination, TenantId, get_db, pagination
from app.models.datasource import DataSource, Dataset

router = APIRouter(prefix="/datasources", tags=["datasources"])


@router.get("")
async def list_datasources(
    tenant_id: TenantId,
    pg: Annotated[Pagination, Depends(pagination)],
    db: AsyncSession = Depends(get_db),
):
    order_col = (
        DataSource.created_at.asc() if pg.order == "asc" else DataSource.created_at.desc()
    )
    ds_result = await db.execute(
        select(DataSource)
        .where(DataSource.tenant_id == tenant_id)
        .order_by(order_col)
        .limit(pg.limit)
    )
    datasources = list(ds_result.scalars().all())
    if not datasources:
        return []

    ds_ids = [ds.id for ds in datasources]
    dataset_result = await db.execute(
        select(Dataset)
        .where(Dataset.datasource_id.in_(ds_ids))
        .order_by(Dataset.created_at.desc())
    )
    all_datasets = list(dataset_result.scalars().all())

    datasets_by_ds: dict[str, list[Dataset]] = {}
    for d in all_datasets:
        datasets_by_ds.setdefault(d.datasource_id, []).append(d)

    return [
        {
            "id": ds.id,
            "name": ds.name,
            "type": ds.type.value,
            "status": ds.status.value,
            "datasets_count": len(datasets_by_ds.get(ds.id, [])),
            "datasets": [
                {
                    "id": d.id,
                    "table_name": d.table_name,
                    "rows_count": d.rows_count,
                    "last_synced_at": d.last_synced_at.isoformat() if d.last_synced_at else None,
                    "status": d.status.value,
                }
                for d in datasets_by_ds.get(ds.id, [])
            ],
            "created_at": ds.created_at.isoformat(),
        }
        for ds in datasources
    ]


@router.delete("/{datasource_id}")
async def delete_datasource(
    datasource_id: str, tenant_id: TenantId, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(DataSource).where(
            DataSource.id == datasource_id,
            DataSource.tenant_id == tenant_id,
        )
    )
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(404, "Datasource not found")

    ds_result = await db.execute(select(Dataset).where(Dataset.datasource_id == datasource_id))
    datasets = list(ds_result.scalars().all())
    delta_paths = [d.delta_path for d in datasets if d.delta_path]

    # Drop view-registry cache entries so subsequent queries re-register
    # (or fail cleanly) instead of returning a stale view reference.
    from app.services.query.view_registry import invalidate_view_cache
    for d in datasets:
        if d.table_name:
            invalidate_view_cache(d.tenant_id, d.table_name)

    await db.execute(delete(Dataset).where(Dataset.datasource_id == datasource_id))
    await db.execute(delete(DataSource).where(
        DataSource.id == datasource_id,
        DataSource.tenant_id == tenant_id,
    ))
    await db.commit()

    removed = 0
    for delta_path in delta_paths:
        delta_dir = Path(delta_path)
        if delta_dir.exists() and delta_dir.is_dir():
            shutil.rmtree(delta_dir, ignore_errors=True)
            removed += 1

    return {"deleted": True, "delta_files_removed": removed}


@router.post("/cleanup-orphans")
async def cleanup_orphan_delta_files(tenant_id: TenantId, db: AsyncSession = Depends(get_db)):
    """Remove Delta directories whose dataset row no longer exists.

    Matches by exact delta_path against any tenant's Dataset records. A directory
    whose path isn't referenced by ANY Dataset row is safe to remove as an orphan.
    Caller must be authorized for their tenant; the operation is global by
    necessity (orphans have no tenant tag left on disk), but the caller's
    tenant_id is required for auditability.
    """
    from app.config import settings

    result = await db.execute(select(Dataset))
    all_valid_paths = {Path(d.delta_path).resolve() for d in result.scalars().all() if d.delta_path}

    # Anchor relative delta_storage at python-api root so the resolved paths line
    # up regardless of the uvicorn launch CWD (otherwise valid dirs can be
    # mis-classified as orphans → silent data loss).
    delta_root = Path(settings.delta_storage)
    if not delta_root.is_absolute():
        delta_root = (Path(__file__).resolve().parents[2] / delta_root).resolve()
    if not delta_root.exists():
        return {"removed": 0, "kept": 0}

    removed = 0
    kept = 0
    for entry in delta_root.iterdir():
        if not entry.is_dir():
            continue
        if entry.resolve() in all_valid_paths:
            kept += 1
        else:
            shutil.rmtree(entry, ignore_errors=True)
            removed += 1

    return {"removed": removed, "kept": kept, "requested_by_tenant": tenant_id}
