"""
Project Pydantic schemas.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ProjectBase(BaseModel):
    """Base project schema."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    datahub_dataset_urn: Optional[str] = None


class ProjectCreate(ProjectBase):
    """Project creation schema."""

    omaha_config: Optional[str] = None  # YAML text


class ProjectUpdate(BaseModel):
    """Project update schema."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    datahub_dataset_urn: Optional[str] = None
    omaha_config: Optional[str] = None


class ProjectInDB(ProjectBase):
    """Project in database schema."""

    id: int
    owner_id: int
    omaha_config: Optional[str] = None
    project_metadata: dict = {}
    setup_stage: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class Project(ProjectInDB):
    """Project response schema."""

    pass


class ProjectWithOwner(Project):
    """Project with owner information."""

    owner_email: str
    owner_username: str
