import uuid
import json
import pandas as pd
from datetime import datetime, timezone
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.sqlite import SQLiteConnector
from app.connectors.postgres import PostgresConnector
from app.connectors.mysql import MySQLConnector
from app.connectors.file import FileConnector
from app.services.ingest.delta_writer import sync_to_delta
from app.services.ingest.schema_inferrer import infer_columns
from app.core.crypto import encrypt_config
from app.core.locks import ingest_lock
from app.models.datasource import DataSource, DataSourceType, Dataset, DatasetStatus
from app.schemas.ingest import IngestRequest, IngestResponse, ColumnInfo, TableDiscovery


CONNECTOR_MAP = {
    "sqlite": SQLiteConnector,
    "postgres": PostgresConnector,
    "mysql": MySQLConnector,
    "csv": FileConnector,
    "excel": FileConnector,
}


async def run_ingest(
    request: IngestRequest, file: UploadFile | None = None, db: AsyncSession | None = None,
    tenant_id: str = "default",
) -> IngestResponse:
    config = request.connection.model_dump() if request.connection else {}

    if request.type in ("csv", "excel") and file:
        config["file_type"] = request.type
        saved_path = await FileConnector.save_upload(file, "/tmp/ingest")
        config["path"] = saved_path

    connector_class = CONNECTOR_MAP.get(request.type)
    if not connector_class:
        raise ValueError(f"不支持的连接类型: {request.type}. 支持: csv, excel, mysql, postgres, sqlite")

    connector = connector_class(config)
    try:
        await connector.connect()
        tables = await connector.discover_tables()
        if not tables:
            raise ValueError("No tables found in data source")

        table = tables[0]
        # Serialize concurrent ingests of the same (tenant, table) to avoid
        # racing on dataset_id allocation and Delta writes.
        async with ingest_lock.for_key(f"{tenant_id}::{table}"):
            sample_data = await connector.sample_data(table, rows=1000)
            df_sample = pd.DataFrame(sample_data)
            columns = infer_columns(df_sample)

            full_data = await connector.sample_data(table, rows=0)
            df_full = pd.DataFrame(full_data)
            rows_count = len(df_full) if not df_full.empty else 0

            # Reuse existing dataset for the same (tenant, table) to avoid orphan Delta dirs.
            existing_dataset = None
            if db is not None:
                from sqlalchemy import select
                q = await db.execute(
                    select(Dataset)
                    .where(Dataset.tenant_id == tenant_id, Dataset.table_name == table)
                    .order_by(Dataset.created_at.desc())
                    .limit(1)
                )
                existing_dataset = q.scalar_one_or_none()

            dataset_id = existing_dataset.id if existing_dataset else str(uuid.uuid4())[:8]
            delta_path = sync_to_delta(df_full, table, dataset_id)

            if db is not None:
                if existing_dataset:
                    existing_dataset.rows_count = rows_count
                    existing_dataset.last_synced_at = datetime.now(timezone.utc)
                    existing_dataset.status = DatasetStatus.ready
                    existing_dataset.delta_path = delta_path
                    # Refresh parent DataSource config so rotated credentials take effect.
                    parent_result = await db.execute(
                        select(DataSource).where(DataSource.id == existing_dataset.datasource_id)
                    )
                    parent = parent_result.scalar_one_or_none()
                    if parent:
                        parent.config = json.dumps(encrypt_config(config))
                else:
                    datasource = DataSource(
                        id=str(uuid.uuid4())[:8],
                        tenant_id=tenant_id,
                        name=f"{request.type}-{table}",
                        type=DataSourceType(request.type) if request.type in [t.value for t in DataSourceType] else DataSourceType.csv,
                        config=json.dumps(encrypt_config(config)),
                    )
                    db.add(datasource)
                    await db.flush()

                    db.add(Dataset(
                        id=dataset_id,
                        datasource_id=datasource.id,
                        tenant_id=tenant_id,
                        table_name=table,
                        rows_count=rows_count,
                        last_synced_at=datetime.now(timezone.utc),
                        sync_schedule="manual",
                        status=DatasetStatus.ready,
                        delta_path=delta_path,
                    ))
                await db.commit()

            return IngestResponse(
                dataset_id=dataset_id,
                table_name=table,
                rows_count=rows_count,
                columns=[ColumnInfo(**c) for c in columns],
                delta_path=delta_path,
                status="ready",
            )
    finally:
        await connector.close()


async def discover_source(request: IngestRequest, file: UploadFile | None = None) -> TableDiscovery:
    """Discover tables and columns without syncing data."""
    config = request.connection.model_dump() if request.connection else {}

    if request.type in ("csv", "excel") and file:
        config["file_type"] = request.type
        saved_path = await FileConnector.save_upload(file, "/tmp/ingest")
        config["path"] = saved_path

    connector_class = CONNECTOR_MAP.get(request.type)
    if not connector_class:
        raise ValueError(f"不支持的连接类型: {request.type}. 支持: csv, excel, mysql, postgres, sqlite")

    connector = connector_class(config)
    try:
        await connector.connect()
        tables = await connector.discover_tables()
        columns = {}
        sample_rows = {}
        for t in tables:
            sample = await connector.sample_data(t, rows=50)
            if sample:
                df = pd.DataFrame(sample)
                columns[t] = [ColumnInfo(**c) for c in infer_columns(df)]
                sample_rows[t] = sample[:5]

        return TableDiscovery(tables=tables, columns=columns, sample_rows=sample_rows)
    finally:
        await connector.close()
