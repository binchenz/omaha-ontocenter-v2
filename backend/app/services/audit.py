"""Audit log service — write and query audit records."""
from typing import Optional
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    detail: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        project_id=project_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    return entry


def get_audit_logs(
    db: Session,
    project_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AuditLog]:
    q = db.query(AuditLog)
    if project_id is not None:
        q = q.filter(AuditLog.project_id == project_id)
    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if action is not None:
        q = q.filter(AuditLog.action == action)
    return q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
