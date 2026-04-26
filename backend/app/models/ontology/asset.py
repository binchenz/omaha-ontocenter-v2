"""
Asset models for dataset assets and data lineage.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class DatasetAsset(Base):
    """Dataset asset model for saved query results and data extracts."""

    __tablename__ = "dataset_assets"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)

    # Asset definition
    base_object = Column(String, nullable=False)  # Base ontology object
    selected_columns = Column(JSON, default=[])  # List of selected columns/properties
    filters = Column(JSON, default={})  # Filter conditions
    joins = Column(JSON, default=[])  # Join definitions

    # Metadata
    row_count = Column(Integer)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", backref="assets")
    creator = relationship("User", backref="created_assets")
    lineage = relationship("DataLineage", back_populates="asset", cascade="all, delete-orphan")


class DataLineage(Base):
    """Data lineage model for tracking data transformations and dependencies."""

    __tablename__ = "data_lineage"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("dataset_assets.id"), nullable=False)

    # Lineage information
    lineage_type = Column(String, nullable=False)  # e.g., 'query', 'transformation', 'aggregation'
    source_type = Column(String, nullable=False)  # e.g., 'table', 'asset', 'query'
    source_id = Column(String)  # ID of the source (table name, asset ID, etc.)
    source_name = Column(String)  # Human-readable source name
    transformation = Column(JSON, default={})  # Transformation details (SQL, filters, etc.)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    asset = relationship("DatasetAsset", back_populates="lineage")
