"""Watchlist model for user's stock watchlist."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class Watchlist(Base):
    """User's stock watchlist."""

    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ts_code = Column(String(20), nullable=False, index=True)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    note = Column(Text, nullable=True)

    # Relationship
    user = relationship("User", back_populates="watchlist")

    __table_args__ = (
        Index('ix_watchlist_user_id', 'user_id'),
        Index('ix_watchlist_ts_code', 'ts_code'),
    )
