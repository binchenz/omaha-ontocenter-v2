"""
Query history model.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class QueryHistory(Base):
    """Query history model."""

    __tablename__ = "query_history"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Query details
    natural_language_query = Column(Text, nullable=False)
    generated_sql = Column(Text)
    object_type = Column(String)  # e.g., "Product", "Customer"

    # Results
    result_data = Column(JSON)  # Store query results
    result_count = Column(Integer)
    execution_time = Column(Float)  # in seconds

    # Status
    status = Column(String, default="pending")  # pending, success, error
    error_message = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", back_populates="query_history")
    user = relationship("User", back_populates="query_history")
