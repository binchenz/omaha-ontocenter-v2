"""PublicQueryLog model for tracking public API queries."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class PublicQueryLog(Base):
    __tablename__ = "public_query_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    query_type = Column(String(50))
    object_type = Column(String(50))
    filters = Column(JSON)  # Works with both PostgreSQL and SQLite
    result_count = Column(Integer)
    execution_time_ms = Column(Integer)
    is_public = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", backref="public_query_logs")
