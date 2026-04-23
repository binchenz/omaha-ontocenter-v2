"""Pipeline model — defines a scheduled data sync job."""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Pipeline(Base):
    """A scheduled job that syncs data from a source connector to a local SQLite table.

    schedule examples: "0 * * * *" (hourly), "0 0 * * *" (daily), "*/30 * * * *" (every 30 min)
    status: active | paused
    """

    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)

    # Source: which datasource + object to pull from
    datasource_id = Column(String(100), nullable=False)   # references datasource id in YAML config
    object_type = Column(String(100), nullable=False)     # ontology object name
    filters = Column(JSON, default=[])                    # optional filter conditions

    # Target: local SQLite table name
    target_table = Column(String(100), nullable=False)

    # Schedule
    schedule = Column(String(50), nullable=False, default="0 * * * *")  # cron expression
    status = Column(String(20), nullable=False, default="active")        # active | paused

    # Tracking
    last_run_at = Column(DateTime(timezone=True))
    last_run_status = Column(String(20))   # success | error | running
    last_run_rows = Column(Integer)
    last_error = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    project = relationship("Project", back_populates="pipelines")
