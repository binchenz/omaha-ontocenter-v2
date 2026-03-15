"""
Query endpoints for Object Explorer.
"""
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
import json
from decimal import Decimal

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.query_history import QueryHistory
from app.api.deps import get_current_user
from app.services.omaha import omaha_service

router = APIRouter()


def convert_decimals(obj):
    """Convert Decimal objects to float for JSON serialization."""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


class QueryObjectsRequest(BaseModel):
    """Request schema for querying objects."""

    object_type: str
    filters: Optional[Dict[str, Any]] = None
    limit: int = 100


class QueryObjectsResponse(BaseModel):
    """Response schema for querying objects."""

    success: bool
    data: Optional[List[Dict[str, Any]]] = None
    count: Optional[int] = None
    error: Optional[str] = None


@router.post("/{project_id}/query", response_model=QueryObjectsResponse)
async def query_objects(
    project_id: int,
    request: QueryObjectsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Query objects from a project."""
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    if not project.omaha_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no Omaha configuration",
        )

    # Query objects
    result = omaha_service.query_objects(
        project.omaha_config,
        request.object_type,
        request.filters,
        request.limit,
    )

    # Convert Decimal objects before saving to database
    result_data_converted = convert_decimals(result.get("data"))

    # Save to query history
    query_history = QueryHistory(
        project_id=project_id,
        user_id=current_user.id,
        natural_language_query=f"Query {request.object_type}",
        object_type=request.object_type,
        result_data=result_data_converted,
        result_count=result.get("count"),
        status="success" if result.get("success") else "error",
        error_message=result.get("error"),
    )
    db.add(query_history)
    db.commit()

    return result


@router.get("/{project_id}/objects")
async def list_object_types(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List available object types in a project."""
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    if not project.omaha_config:
        return {"objects": []}

    # Build ontology
    result = omaha_service.build_ontology(project.omaha_config)

    if not result.get("valid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Omaha configuration",
        )

    ontology = result.get("ontology", {})
    objects = ontology.get("objects", [])

    # Extract object names from the list
    object_names = [obj.get("name") for obj in objects if obj.get("name")]

    return {"objects": object_names}


@router.get("/{project_id}/history")
async def get_query_history(
    project_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Get query history for a project."""
    # Get project
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    # Get history
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
