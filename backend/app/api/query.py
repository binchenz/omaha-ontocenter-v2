"""
Query endpoints for Object Explorer.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.query_history import QueryHistory
from app.api.deps import get_current_user, get_project_for_owner
from app.services.omaha import omaha_service
from app.services.audit import log_action

router = APIRouter()


def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


def _require_config(project: Project) -> str:
    """Return omaha_config or raise 400 if missing."""
    if not project.omaha_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no Omaha configuration",
        )
    return project.omaha_config


class QueryObjectsRequest(BaseModel):
    """Request schema for querying objects."""

    object_type: str
    selected_columns: Optional[List[str]] = None
    filters: Optional[List[Dict[str, Any]]] = None
    joins: Optional[List[Dict[str, Any]]] = None
    limit: Optional[int] = None


class QueryObjectsResponse(BaseModel):
    """Response schema for querying objects."""

    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = None
    error: Optional[str] = None


@router.get("/{project_id}/relationships/{object_type}")
async def get_relationships(
    project_id: int,
    object_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get available relationships for an object type."""
    project = get_project_for_owner(project_id, current_user, db)
    config = _require_config(project)
    try:
        relationships = omaha_service.get_relationships(config, object_type)
        return {"relationships": relationships}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get relationships: {str(e)}",
        )


@router.post("/{project_id}/query", response_model=QueryObjectsResponse)
async def query_objects(
    project_id: int,
    request: QueryObjectsRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query objects from a project."""
    project = get_project_for_owner(project_id, current_user, db)
    config = _require_config(project)

    result = omaha_service.query_objects(
        config,
        request.object_type,
        request.selected_columns,
        request.filters,
        request.joins,
        request.limit,
    )

    query_history = QueryHistory(
        project_id=project_id,
        user_id=current_user.id,
        natural_language_query=f"Query {request.object_type}",
        object_type=request.object_type,
        result_data=convert_decimals(result.get("data")),
        result_count=result.get("count"),
        status="success" if result.get("success") else "error",
        error_message=result.get("error"),
    )
    db.add(query_history)
    log_action(
        db,
        action="query.run",
        user_id=current_user.id,
        project_id=project_id,
        resource_type="query",
        resource_id=request.object_type,
        detail={"object_type": request.object_type, "filter_count": len(request.filters or []), "success": result.get("success")},
        ip_address=http_request.client.host if http_request.client else None,
        commit=False,
    )
    db.commit()

    return result


@router.get("/{project_id}/objects")
async def list_object_types(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List available object types in a project."""
    project = get_project_for_owner(project_id, current_user, db)

    if not project.omaha_config:
        return {"objects": []}

    result = omaha_service.build_ontology(project.omaha_config)
    if not result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Omaha configuration",
        )

    objects = result.get("ontology", {}).get("objects", [])
    return {"objects": [obj.get("name") for obj in objects if obj.get("name")]}


@router.get("/{project_id}/schema/{object_type}")
async def get_object_schema(
    project_id: int,
    object_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get schema (columns) for an object type."""
    project = get_project_for_owner(project_id, current_user, db)
    config = _require_config(project)

    result = omaha_service.get_object_schema(config, object_type)
    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to get schema"),
        )
    return result


@router.get("/{project_id}/history")
async def get_query_history(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get query history for a project."""
    get_project_for_owner(project_id, current_user, db)

    history = (
        db.query(QueryHistory)
        .filter(QueryHistory.project_id == project_id)
        .order_by(QueryHistory.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": h.id,
            "natural_language_query": h.natural_language_query,
            "object_type": h.object_type,
            "result_count": h.result_count,
            "status": h.status,
            "error_message": h.error_message,
            "created_at": h.created_at.isoformat(),
        }
        for h in history
    ]
