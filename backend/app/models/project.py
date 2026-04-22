"""
Project model.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Project(Base):
    """Project model."""

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # DataHub integration
    datahub_dataset_urn = Column(String, index=True)

    # Omaha configuration (stored as YAML text)
    omaha_config = Column(Text)

    # Project metadata
    project_metadata = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="projects")
    query_history = relationship("QueryHistory", back_populates="project")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
