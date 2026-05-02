from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.ingest import IngestRequest, IngestResponse, TableDiscovery
from app.services.ingest.coordinator import run_ingest, discover_source

router = APIRouter(prefix="/ingest", tags=["ingest"])


def _build_request(type: str, host: str, port: int, database: str, user: str, password: str, path: str) -> IngestRequest:
    return IngestRequest(
        type=type,
        connection={"host": host, "port": port, "database": database, "user": user, "password": password, "path": path} if host or path else None,
    )


@router.post("/discover")
async def discover(
    type: str = Form(...),
    host: str = Form(""), port: int = Form(5432),
    database: str = Form(""), user: str = Form(""),
    password: str = Form(""), path: str = Form(""),
    file: UploadFile | None = File(None),
) -> TableDiscovery:
    try:
        return await discover_source(_build_request(type, host, port, database, user, password, path), file)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("", response_model=IngestResponse)
async def ingest(
    type: str = Form(...),
    host: str = Form(""), port: int = Form(5432),
    database: str = Form(""), user: str = Form(""),
    password: str = Form(""), path: str = Form(""),
    tenant_id: str = Form("default"),
    file: UploadFile | None = File(None),
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    try:
        return await run_ingest(
            _build_request(type, host, port, database, user, password, path),
            file, db=db, tenant_id=tenant_id,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
