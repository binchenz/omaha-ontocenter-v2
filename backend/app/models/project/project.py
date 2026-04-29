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
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=True, index=True)

    # Omaha configuration (stored as YAML text)
    omaha_config = Column(Text)

    # Project metadata
    project_metadata = Column(JSON, default={})

    # Setup stage for conversational ingestion workflow
    setup_stage = Column(String(20), nullable=False, default="idle", server_default="idle")

    def __init__(self, **kwargs):
        kwargs.setdefault("setup_stage", "idle")
        super().__init__(**kwargs)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="projects")
    tenant = relationship("Tenant", back_populates="projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    pipelines = relationship("Pipeline", back_populates="project", cascade="all, delete-orphan")
