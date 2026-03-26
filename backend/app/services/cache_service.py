"""Cache service for querying cached data."""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.cached_stock import CachedStock


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
