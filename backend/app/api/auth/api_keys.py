"""API Key management endpoints."""
import secrets
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth.user import User
from app.models.auth.api_key import ProjectApiKey
from app.api.deps import get_current_user, get_project_for_owner
from app.mcp.auth import _hash_key

router = APIRouter()


class ApiKeyCreate(BaseModel):
    name: str
    expires_at: Optional[datetime] = None


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyCreated(ApiKeyResponse):
    key: str  # only returned once at creation


@router.post("/{project_id}/api-keys", response_model=ApiKeyCreated,
             status_code=status.HTTP_201_CREATED)
def create_api_key(
    project_id: int,
    body: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a new API key for a project."""
    get_project_for_owner(project_id, current_user, db)
    random_part = secrets.token_hex(16)  # 32 chars
    key = f"omaha_{project_id}_{random_part}"
    api_key = ProjectApiKey(
        project_id=project_id,
        name=body.name,
        key_hash=_hash_key(key),
        key_prefix=random_part[:8],
        expires_at=body.expires_at,
        created_by=current_user.id,
    )
    db.add(api_key)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create API key")
    db.refresh(api_key)
    return {**ApiKeyResponse.model_validate(api_key).model_dump(), "key": key}


@router.get("/{project_id}/api-keys", response_model=List[ApiKeyResponse])
def list_api_keys(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all API keys for a project."""
    get_project_for_owner(project_id, current_user, db)
    return db.query(ProjectApiKey).filter(
        ProjectApiKey.project_id == project_id
    ).all()


@router.delete("/{project_id}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    project_id: int,
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Revoke (deactivate) an API key."""
    get_project_for_owner(project_id, current_user, db)
    api_key = db.query(ProjectApiKey).filter(
        ProjectApiKey.id == key_id,
        ProjectApiKey.project_id == project_id,
    ).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    api_key.is_active = False
    db.commit()
