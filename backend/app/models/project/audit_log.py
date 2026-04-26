"""AuditLog model — records key user actions for compliance and debugging."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class AuditLog(Base):
    """Immutable record of a user action.

    action examples: login, logout, project.create, project.update,
                     query.run, config.save, member.add, member.remove
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50))   # project | query | config | member | asset
    resource_id = Column(String(100))    # id of the affected resource
    detail = Column(JSON)                # extra context (e.g. object_type, filter count)
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User")
