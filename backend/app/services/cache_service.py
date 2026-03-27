"""Cache service for querying cached data."""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.cached_stock import CachedStock
from app.models.cached_financial import CachedFinancialIndicator
from app.models.cached_financial_statements import CachedIncomeStatement, CachedBalanceSheet, CachedCashFlow
from app.services.semantic_formatter import SemanticTypeFormatter


class CacheService:
    """Service for querying cached data."""

    def __init__(self, db: Session):
        self.db = db

    def query_stocks(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Query cached stocks with filters."""
        query = self.db.query(CachedStock)

        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(CachedStock, field):
                    conditions.append(getattr(CachedStock, field) == value)
            if conditions:
                query = query.filter(and_(*conditions))

        stocks = query.offset(offset).limit(limit).all()
        return [
            {
                "ts_code": s.ts_code,
                "name": s.name,
                "industry": s.industry,
                "area": s.area,
                "market": s.market,
                "list_date": s.list_date,
                "list_status": s.list_status,
            }
            for s in stocks
        ]

    def query_financial_indicators(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        format_output: bool = False
    ) -> List[Dict[str, Any]]:
        """Query cached financial indicators with filters."""
        query = self.db.query(CachedFinancialIndicator)

        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(CachedFinancialIndicator, field):
                    conditions.append(getattr(CachedFinancialIndicator, field) == value)
            if conditions:
                query = query.filter(and_(*conditions))

        query = query.order_by(CachedFinancialIndicator.end_date.desc())
        records = query.offset(offset).limit(limit).all()

        result = []
        for r in records:
            data = {
                "ts_code": r.ts_code,
                "end_date": SemanticTypeFormatter.format_value(r.end_date, 'date') if format_output else r.end_date,
                "roe": SemanticTypeFormatter.format_value(r.roe, 'percentage') if format_output and r.roe is not None else (float(r.roe) if r.roe is not None else None),
                "roa": SemanticTypeFormatter.format_value(r.roa, 'percentage') if format_output and r.roa is not None else (float(r.roa) if r.roa is not None else None),
                "grossprofit_margin": SemanticTypeFormatter.format_value(r.grossprofit_margin, 'percentage') if format_output and r.grossprofit_margin is not None else (float(r.grossprofit_margin) if r.grossprofit_margin is not None else None),
                "netprofit_margin": SemanticTypeFormatter.format_value(r.netprofit_margin, 'percentage') if format_output and r.netprofit_margin is not None else (float(r.netprofit_margin) if r.netprofit_margin is not None else None),
                "debt_to_assets": SemanticTypeFormatter.format_value(r.debt_to_assets, 'percentage') if format_output and r.debt_to_assets is not None else (float(r.debt_to_assets) if r.debt_to_assets is not None else None),
            }
            # 计算属性: financial_health_score
            raw_data = {"roe": float(r.roe) if r.roe else 0, "roa": float(r.roa) if r.roa else 0, "grossprofit_margin": float(r.grossprofit_margin) if r.grossprofit_margin else 0}
            health_score = SemanticTypeFormatter.compute_property("{roe} * 0.4 + {roa} * 0.3 + {grossprofit_margin} * 0.3", raw_data)
            if health_score is not None:
                data["financial_health_score"] = SemanticTypeFormatter.format_value(health_score, 'percentage') if format_output else health_score
            result.append(data)
        return result

    def get_financial_indicator_schema(self) -> Dict[str, Any]:
        """Get financial indicator schema definition."""
        return {
            "object_type": "FinancialIndicator",
            "fields": [
                {"name": "ts_code", "type": "string", "description": "Stock code"},
                {"name": "end_date", "type": "string", "description": "Report period (YYYYMMDD)"},
                {"name": "roe", "type": "number", "description": "Return on equity (%)"},
                {"name": "roa", "type": "number", "description": "Return on assets (%)"},
                {"name": "grossprofit_margin", "type": "number", "description": "Gross profit margin (%)"},
                {"name": "netprofit_margin", "type": "number", "description": "Net profit margin (%)"},
                {"name": "debt_to_assets", "type": "number", "description": "Debt to assets ratio (%)"},
            ],
        }

    def get_stock_schema(self) -> Dict[str, Any]:
        """Get stock schema definition."""
        return {
            "object_type": "Stock",
            "fields": [
                {"name": "ts_code", "type": "string", "description": "Stock code"},
                {"name": "name", "type": "string", "description": "Stock name"},
                {"name": "industry", "type": "string", "description": "Industry"},
                {"name": "area", "type": "string", "description": "Area"},
                {"name": "market", "type": "string", "description": "Market"},
                {"name": "list_date", "type": "string", "description": "List date"},
                {"name": "list_status", "type": "string", "description": "List status"},
            ],
        }

    def query_income_statements(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        format_output: bool = False
    ) -> List[Dict[str, Any]]:
        """Query cached income statements."""
        query = self.db.query(CachedIncomeStatement)
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(CachedIncomeStatement, field):
                    conditions.append(getattr(CachedIncomeStatement, field) == value)
            if conditions:
                query = query.filter(and_(*conditions))
        query = query.order_by(CachedIncomeStatement.end_date.desc())
        records = query.offset(offset).limit(limit).all()
        return [
            {
                "ts_code": r.ts_code,
                "end_date": SemanticTypeFormatter.format_value(r.end_date, 'date') if format_output else r.end_date,
                "total_revenue": SemanticTypeFormatter.format_value(r.total_revenue, 'currency_cny') if format_output and r.total_revenue else (float(r.total_revenue) if r.total_revenue else None),
                "operate_profit": SemanticTypeFormatter.format_value(r.operate_profit, 'currency_cny') if format_output and r.operate_profit else (float(r.operate_profit) if r.operate_profit else None),
                "n_income": SemanticTypeFormatter.format_value(r.n_income, 'currency_cny') if format_output and r.n_income else (float(r.n_income) if r.n_income else None),
            }
            for r in records
        ]

    def query_balance_sheets(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        format_output: bool = False
    ) -> List[Dict[str, Any]]:
        """Query cached balance sheets."""
        query = self.db.query(CachedBalanceSheet)
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(CachedBalanceSheet, field):
                    conditions.append(getattr(CachedBalanceSheet, field) == value)
            if conditions:
                query = query.filter(and_(*conditions))
        query = query.order_by(CachedBalanceSheet.end_date.desc())
        records = query.offset(offset).limit(limit).all()
        return [
            {
                "ts_code": r.ts_code,
                "end_date": SemanticTypeFormatter.format_value(r.end_date, 'date') if format_output else r.end_date,
                "total_assets": SemanticTypeFormatter.format_value(r.total_assets, 'currency_cny') if format_output and r.total_assets else (float(r.total_assets) if r.total_assets else None),
                "total_liab": SemanticTypeFormatter.format_value(r.total_liab, 'currency_cny') if format_output and r.total_liab else (float(r.total_liab) if r.total_liab else None),
                "total_hldr_eqy_exc_min_int": SemanticTypeFormatter.format_value(r.total_hldr_eqy_exc_min_int, 'currency_cny') if format_output and r.total_hldr_eqy_exc_min_int else (float(r.total_hldr_eqy_exc_min_int) if r.total_hldr_eqy_exc_min_int else None),
            }
            for r in records
        ]

    def query_cash_flows(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
        format_output: bool = False
    ) -> List[Dict[str, Any]]:
        """Query cached cash flows."""
        query = self.db.query(CachedCashFlow)
        if filters:
            conditions = []
            for field, value in filters.items():
                if hasattr(CachedCashFlow, field):
                    conditions.append(getattr(CachedCashFlow, field) == value)
            if conditions:
                query = query.filter(and_(*conditions))
        query = query.order_by(CachedCashFlow.end_date.desc())
        records = query.offset(offset).limit(limit).all()
        return [
            {
                "ts_code": r.ts_code,
                "end_date": SemanticTypeFormatter.format_value(r.end_date, 'date') if format_output else r.end_date,
                "n_cashflow_act": SemanticTypeFormatter.format_value(r.n_cashflow_act, 'currency_cny') if format_output and r.n_cashflow_act else (float(r.n_cashflow_act) if r.n_cashflow_act else None),
                "free_cashflow": SemanticTypeFormatter.format_value(r.free_cashflow, 'currency_cny') if format_output and r.free_cashflow else (float(r.free_cashflow) if r.free_cashflow else None),
            }
            for r in records
        ]
