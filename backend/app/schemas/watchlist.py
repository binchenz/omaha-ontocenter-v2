"""Watchlist schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WatchlistBase(BaseModel):
    """Base watchlist schema."""
    ts_code: str
    note: Optional[str] = None


class WatchlistCreate(WatchlistBase):
    """Schema for creating watchlist item."""
    pass


class WatchlistUpdate(BaseModel):
    """Schema for updating watchlist item."""
    note: Optional[str] = None


class WatchlistResponse(WatchlistBase):
    """Schema for watchlist response."""
    id: int
    user_id: int
    added_at: datetime

    class Config:
        from_attributes = True
