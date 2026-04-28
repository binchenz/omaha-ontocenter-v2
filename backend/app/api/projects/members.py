"""Project membership API — invite users, manage roles, list members."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from typing import Optional

from app.database import get_db
from app.api.deps import get_current_user, get_project_for_owner
from app.models.auth.user import User
from app.models.project.project_member import ProjectMember

router = APIRouter(prefix="/projects", tags=["members"])

VALID_ROLES = {"owner", "editor", "viewer"}


class AddMemberRequest(BaseModel):
    username: str
    role: str = "viewer"


class UpdateRoleRequest(BaseModel):
    role: str


@router.get("/{project_id}/members")
def list_members(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all members of a project. Accessible by any member."""
    _require_member(project_id, user.id, db)
    members = db.query(ProjectMember).options(joinedload(ProjectMember.user)).filter(ProjectMember.project_id == project_id).all()
    return {
        "members": [
            {
                "user_id": m.user_id,
                "username": m.user.username,
                "email": m.user.email,
                "role": m.role,
                "joined_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in members
        ]
    }


@router.post("/{project_id}/members")
def add_member(
    project_id: int,
    req: AddMemberRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add a user to the project. Only owner can do this."""
    get_project_for_owner(project_id, user, db)

    if req.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    target = db.query(User).filter(User.username == req.username).first()
    if not target:
        raise HTTPException(status_code=404, detail=f"User '{req.username}' not found")

    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == target.id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member of this project")

    member = ProjectMember(project_id=project_id, user_id=target.id, role=req.role)
    db.add(member)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to add member")
    db.refresh(member)
    return {"user_id": target.id, "username": target.username, "role": member.role}


@router.put("/{project_id}/members/{member_user_id}")
def update_member_role(
    project_id: int,
    member_user_id: int,
    req: UpdateRoleRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change a member's role. Only owner can do this."""
    get_project_for_owner(project_id, user, db)

    if req.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == member_user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.role = req.role
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update member role")
    return {"user_id": member_user_id, "role": req.role}


@router.delete("/{project_id}/members/{member_user_id}")
def remove_member(
    project_id: int,
    member_user_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a member from the project. Owner can remove anyone; members can remove themselves."""
    if user.id == member_user_id:
        _require_member(project_id, user.id, db)
    else:
        get_project_for_owner(project_id, user, db)

    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == member_user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to remove member")
    return {"removed": True}


def _require_member(project_id: int, user_id: int, db: Session) -> Optional[ProjectMember]:
    """Raise 403 if user is not a member or owner of the project. Returns None for owners."""
    from app.models.project.project import Project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.owner_id == user_id:
        return None  # owner always has access
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Not a member of this project")
    return member
