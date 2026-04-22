"""Audit log API — query audit records for a project."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user, get_project_for_owner
from app.models.user import User
from app.services.audit import get_audit_logs

router = APIRouter(prefix="/projects", tags=["audit"])


@router.get("/{project_id}/audit-logs")
def list_audit_logs(
    project_id: int,
    action: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List audit logs for a project. Only project owner can access."""
    get_project_for_owner(project_id, user, db)
    logs = get_audit_logs(db, project_id=project_id, action=action, limit=limit, offset=offset)
    return {
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.user.username if log.user else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "detail": log.detail,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": len(logs),
    }
