import os
import sqlite3
import yaml
from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user, get_project_for_owner
from app.models.user import User
from app.models.project import Project
from app.services.omaha import omaha_service
from app.connectors import get_connector
from app.connectors.csv_connector import CSVConnector

router = APIRouter(prefix="/datasources", tags=["datasources"])

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
CSV_DATASOURCE_ID = "csv_imported"


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
    project = get_project_for_owner(project_id, user, db)

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

    _patch_yaml_config(project, table_name, columns, db_path, db)

    return {
        "success": True,
        "table_name": table_name,
        "columns": [{"name": c.name, "type": c.type, "nullable": c.nullable} for c in columns],
        "file_path": file_path,
    }


@router.get("/{project_id}/tables")
def list_imported_tables(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List tables in the project's local imported SQLite database."""
    get_project_for_owner(project_id, user, db)
    db_path = os.path.join(DATA_DIR, str(project_id), "imported.db")
    if not os.path.exists(db_path):
        return {"tables": []}
    conn = sqlite3.connect(db_path)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()]
        return {"tables": tables}
    finally:
        conn.close()


def _patch_yaml_config(project: Project, table_name: str, columns, db_path: str, db: Session):
    """Add or update csv_imported datasource + object in the project's YAML config.

    Commits immediately — intentional, so the config is persisted even if the
    caller's response fails after this point (file is already written to disk).
    """
    config_yaml = project.omaha_config or ""
    if isinstance(config_yaml, bytes):
        config_yaml = config_yaml.decode("utf-8")

    try:
        config = yaml.safe_load(config_yaml) or {}
    except Exception:
        config = {}

    # Ensure csv_imported datasource exists
    datasources = config.setdefault("datasources", [])
    if not any(ds.get("id") == CSV_DATASOURCE_ID for ds in datasources):
        datasources.append({
            "id": CSV_DATASOURCE_ID,
            "name": "CSV/Excel 导入数据",
            "type": "sqlite",
            "connection": {"database": db_path},
        })
    else:
        # Update db_path in case it changed
        for ds in datasources:
            if ds.get("id") == CSV_DATASOURCE_ID:
                ds.setdefault("connection", {})["database"] = db_path

    # Add or replace the object for this table
    ontology = config.setdefault("ontology", {})
    objects = ontology.setdefault("objects", [])
    objects = [o for o in objects if o.get("name") != table_name]
    objects.append({
        "name": table_name,
        "datasource": CSV_DATASOURCE_ID,
        "table": table_name,
        "primary_key": "rowid",
        "properties": [
            {"name": c.name, "column": c.name, "type": c.type}
            for c in columns
        ],
    })
    ontology["objects"] = objects
    config["ontology"] = ontology

    project.omaha_config = yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)
    db.commit()
