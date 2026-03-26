"""CachedFinancialIndicator model for storing financial metrics."""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Index
from sqlalchemy.sql import func
from app.database import Base


class CachedFinancialIndicator(Base):
    __tablename__ = "cached_financial_indicators"

    id = Column(Integer, primary_key=True, index=True)
    ts_code = Column(String(20), nullable=False, index=True)
    end_date = Column(String(8), nullable=False, index=True)
    roe = Column(Numeric(10, 2))
    roa = Column(Numeric(10, 2))
    grossprofit_margin = Column(Numeric(10, 2))
    netprofit_margin = Column(Numeric(10, 2))
    debt_to_assets = Column(Numeric(10, 2))
    cached_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_ts_code', 'ts_code'),
        Index('idx_end_date', 'end_date'),
    )
