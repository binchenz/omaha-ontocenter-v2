"""Cached models for IncomeStatement, BalanceSheet, and CashFlow."""
from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.sql import func
from app.database import Base


class CachedIncomeStatement(Base):
    __tablename__ = "cached_income_statements"

    id = Column(Integer, primary_key=True, index=True)
    ts_code = Column(String(20), nullable=False, index=True)
    end_date = Column(String(8), nullable=False, index=True)
    report_type = Column(String(4))
    total_revenue = Column(Numeric(20, 2))
    revenue = Column(Numeric(20, 2))
    total_cogs = Column(Numeric(20, 2))
    operate_profit = Column(Numeric(20, 2))
    total_profit = Column(Numeric(20, 2))
    n_income = Column(Numeric(20, 2))
    n_income_attr_p = Column(Numeric(20, 2))
    ebit = Column(Numeric(20, 2))
    ebitda = Column(Numeric(20, 2))
    cached_at = Column(DateTime(timezone=True), server_default=func.now())


class CachedBalanceSheet(Base):
    __tablename__ = "cached_balance_sheets"

    id = Column(Integer, primary_key=True, index=True)
    ts_code = Column(String(20), nullable=False, index=True)
    end_date = Column(String(8), nullable=False, index=True)
    report_type = Column(String(4))
    total_assets = Column(Numeric(20, 2))
    total_cur_assets = Column(Numeric(20, 2))
    total_nca = Column(Numeric(20, 2))
    money_cap = Column(Numeric(20, 2))
    accounts_receiv = Column(Numeric(20, 2))
    inventories = Column(Numeric(20, 2))
    total_liab = Column(Numeric(20, 2))
    total_cur_liab = Column(Numeric(20, 2))
    total_ncl = Column(Numeric(20, 2))
    total_hldr_eqy_exc_min_int = Column(Numeric(20, 2))
    total_hldr_eqy_inc_min_int = Column(Numeric(20, 2))
    cached_at = Column(DateTime(timezone=True), server_default=func.now())


class CachedCashFlow(Base):
    __tablename__ = "cached_cash_flows"

    id = Column(Integer, primary_key=True, index=True)
    ts_code = Column(String(20), nullable=False, index=True)
    end_date = Column(String(8), nullable=False, index=True)
    report_type = Column(String(4))
    n_cashflow_act = Column(Numeric(20, 2))
    n_cashflow_inv_act = Column(Numeric(20, 2))
    n_cash_flows_fnc_act = Column(Numeric(20, 2))
    c_cash_equ_end_period = Column(Numeric(20, 2))
    c_cash_equ_beg_period = Column(Numeric(20, 2))
    free_cashflow = Column(Numeric(20, 2))
    cached_at = Column(DateTime(timezone=True), server_default=func.now())
