"""Pipeline API — CRUD + manual run trigger."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user, get_project_for_owner
from app.models.user import User
from app.models.pipeline import Pipeline
from app.services.platform.pipeline_runner import run_pipeline
from app.services.platform.scheduler import scheduler

router = APIRouter(prefix="/projects", tags=["pipelines"])


class PipelineCreate(BaseModel):
    name: str
    description: Optional[str] = None
    datasource_id: str
    object_type: str
    filters: list = []
    target_table: str
    schedule: str = "0 * * * *"


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    filters: Optional[list] = None
    target_table: Optional[str] = None
    schedule: Optional[str] = None
    status: Optional[str] = None


def _pipeline_dict(p: Pipeline) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "datasource_id": p.datasource_id,
        "object_type": p.object_type,
        "filters": p.filters,
        "target_table": p.target_table,
        "schedule": p.schedule,
        "status": p.status,
        "last_run_at": p.last_run_at.isoformat() if p.last_run_at else None,
        "last_run_status": p.last_run_status,
        "last_run_rows": p.last_run_rows,
        "last_error": p.last_error,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


@router.get("/{project_id}/pipelines")
def list_pipelines(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_project_for_owner(project_id, user, db)
    pipelines = db.query(Pipeline).filter(Pipeline.project_id == project_id).all()
    return {"pipelines": [_pipeline_dict(p) for p in pipelines]}


@router.post("/{project_id}/pipelines", status_code=201)
def create_pipeline(
    project_id: int,
    req: PipelineCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_project_for_owner(project_id, user, db)
    pipeline = Pipeline(
        project_id=project_id,
        name=req.name,
        description=req.description,
        datasource_id=req.datasource_id,
        object_type=req.object_type,
        filters=req.filters,
        target_table=req.target_table,
        schedule=req.schedule,
    )
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    scheduler.add_pipeline(pipeline.id, pipeline.schedule)
    return _pipeline_dict(pipeline)


@router.put("/{project_id}/pipelines/{pipeline_id}")
def update_pipeline(
    project_id: int,
    pipeline_id: int,
    req: PipelineUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_project_for_owner(project_id, user, db)
    pipeline = _get_pipeline(project_id, pipeline_id, db)
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(pipeline, field, value)
    db.commit()
    db.refresh(pipeline)
    scheduler.sync_pipeline(pipeline.id)
    return _pipeline_dict(pipeline)


@router.delete("/{project_id}/pipelines/{pipeline_id}", status_code=204)
def delete_pipeline(
    project_id: int,
    pipeline_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    get_project_for_owner(project_id, user, db)
    pipeline = _get_pipeline(project_id, pipeline_id, db)
    scheduler.remove_pipeline(pipeline_id)
    db.delete(pipeline)
    db.commit()


@router.post("/{project_id}/pipelines/{pipeline_id}/run")
def run_pipeline_now(
    project_id: int,
    pipeline_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually trigger a pipeline run."""
    project = get_project_for_owner(project_id, user, db)
    pipeline = _get_pipeline(project_id, pipeline_id, db)

    config_yaml = project.omaha_config
    if not config_yaml:
        raise HTTPException(status_code=400, detail="Project has no ontology config")
    if isinstance(config_yaml, bytes):
        config_yaml = config_yaml.decode("utf-8")

    result = run_pipeline(pipeline, config_yaml, db, triggered_by="manual")
    return result


@router.get("/{project_id}/pipelines/{pipeline_id}/runs")
def list_pipeline_runs(
    project_id: int,
    pipeline_id: int,
    limit: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List execution history for a pipeline."""
    get_project_for_owner(project_id, user, db)
    _get_pipeline(project_id, pipeline_id, db)
    from app.models.pipeline_run import PipelineRun
    runs = db.query(PipelineRun).filter(
        PipelineRun.pipeline_id == pipeline_id
    ).order_by(PipelineRun.created_at.desc()).limit(limit).all()
    return {
        "runs": [
            {
                "id": r.id,
                "status": r.status,
                "rows_synced": r.rows_synced,
                "duration_seconds": r.duration_seconds,
                "error_message": r.error_message,
                "triggered_by": r.triggered_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ]
    }


def _get_pipeline(project_id: int, pipeline_id: int, db: Session) -> Pipeline:
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.project_id == project_id,
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline
