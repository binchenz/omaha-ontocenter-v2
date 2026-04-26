"""PipelineRun model — records each execution of a pipeline."""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(20), nullable=False)  # success | error | running
    rows_synced = Column(Integer)
    duration_seconds = Column(Float)
    error_message = Column(Text)
    triggered_by = Column(String(20), default="scheduler")  # scheduler | manual
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    pipeline = relationship("Pipeline")
