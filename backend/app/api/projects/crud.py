"""
Project management endpoints.
"""
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth.user import User
from app.models.project.project import Project
from app.schemas.project.project import (
    Project as ProjectSchema,
    ProjectCreate,
    ProjectUpdate,
)
from app.api.deps import get_current_user, get_project_for_owner
from app.services.platform.audit import log_action

router = APIRouter()


@router.post("/", response_model=ProjectSchema, status_code=status.HTTP_201_CREATED)
def create_project(
    project_in: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new project."""
    project = Project(
        name=project_in.name,
        description=project_in.description,
        datahub_dataset_urn=project_in.datahub_dataset_urn,
        omaha_config=project_in.omaha_config,
        owner_id=current_user.id,
    )
    db.add(project)
    db.flush()  # get project.id without committing
    log_action(db, action="project.create", user_id=current_user.id,
               project_id=project.id, resource_type="project", resource_id=str(project.id), commit=False)
    db.commit()
    db.refresh(project)

    return project


@router.get("/", response_model=List[ProjectSchema])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all projects for current user."""
    projects = (
        db.query(Project)
        .filter(Project.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return projects


@router.get("/{project_id}", response_model=ProjectSchema)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific project."""
    return get_project_for_owner(project_id, current_user, db)


@router.put("/{project_id}", response_model=ProjectSchema)
def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a project."""
    project = get_project_for_owner(project_id, current_user, db)

    update_data = project_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    if "omaha_config" in update_data:
        log_action(db, action="config.save", user_id=current_user.id,
                   project_id=project_id, resource_type="config", resource_id=str(project_id), commit=False)
    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project."""
    project = get_project_for_owner(project_id, current_user, db)
    db.delete(project)
    db.commit()

    return None
