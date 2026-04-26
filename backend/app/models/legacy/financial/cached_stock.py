"""CachedStock model for storing Tushare stock data."""
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class CachedStock(Base):
    __tablename__ = "cached_stocks"

    ts_code = Column(String(20), primary_key=True)
    name = Column(String(50))
    industry = Column(String(50), index=True)
    area = Column(String(50), index=True)
    market = Column(String(20))
    list_date = Column(String(8))
    list_status = Column(String(1))
    cached_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_industry', 'industry'),
        Index('idx_area', 'area'),
    )
