import os
from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user, get_project_for_owner
from app.models.user import User
from app.services.omaha import omaha_service
from app.connectors import get_connector
from app.connectors.csv_connector import CSVConnector

router = APIRouter(prefix="/datasources", tags=["datasources"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


class TestConnectionRequest(BaseModel):
    type: str
    connection: dict


@router.get("/{project_id}/list")
def list_datasources(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = get_project_for_owner(project_id, user, db)
    if not project.omaha_config:
        return {"datasources": []}

    config_yaml = project.omaha_config
    if isinstance(config_yaml, bytes):
        config_yaml = config_yaml.decode("utf-8")

    result = omaha_service.parse_config(config_yaml)
    if not result.get("valid"):
        return {"datasources": []}

    raw_ds = result["config"].get("datasources", [])
    return {
        "datasources": [
            {"id": ds.get("id"), "type": ds.get("type"), "name": ds.get("name", ds.get("id"))}
            for ds in raw_ds
        ]
    }


@router.post("/{project_id}/test")
def test_connection(
    project_id: int,
    req: TestConnectionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_project_for_owner(project_id, user, db)
    try:
        config = req.connection
        if req.type in ("sqlite", "mysql", "postgresql"):
            config = {"type": req.type, **req.connection}
        connector = get_connector(req.type, config)
        connected = connector.test_connection()
        connector.close()
        return {"connected": connected}
    except ValueError as e:
        return {"connected": False, "error": str(e)}


@router.post("/{project_id}/upload")
async def upload_file(
    project_id: int,
    file: UploadFile = File(...),
    table_name: str = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_project_for_owner(project_id, user, db)

    project_data_dir = os.path.join(DATA_DIR, str(project_id))
    uploads_dir = os.path.join(project_data_dir, "uploads")
    os.makedirs(uploads_dir, exist_ok=True)

    file_path = os.path.join(uploads_dir, file.filename or "upload.csv")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    db_path = os.path.join(project_data_dir, "imported.db")
    connector = CSVConnector({"storage_path": uploads_dir, "database": db_path})
    columns = connector.ingest(file_path, table_name)

    return {
        "success": True,
        "table_name": table_name,
        "columns": [{"name": c.name, "type": c.type, "nullable": c.nullable} for c in columns],
        "file_path": file_path,
    }
