"""Watchlist API endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.auth.user import User
from app.models.legacy.financial.watchlist import Watchlist
from app.schemas.legacy.financial.watchlist import WatchlistCreate, WatchlistUpdate, WatchlistResponse
from app.api.deps import get_current_user

router = APIRouter()


@router.get("/", response_model=List[WatchlistResponse])
def list_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's watchlist."""
    items = db.query(Watchlist).filter(Watchlist.user_id == current_user.id).all()
    return items


@router.post("/", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
def add_to_watchlist(
    item: WatchlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add stock to watchlist."""
    # Check if already exists
    existing = db.query(Watchlist).filter(
        Watchlist.user_id == current_user.id,
        Watchlist.ts_code == item.ts_code
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stock already in watchlist"
        )

    watchlist_item = Watchlist(
        user_id=current_user.id,
        ts_code=item.ts_code,
        note=item.note
    )
    db.add(watchlist_item)
    db.commit()
    db.refresh(watchlist_item)
    return watchlist_item


@router.patch("/{item_id}", response_model=WatchlistResponse)
def update_watchlist_item(
    item_id: int,
    item: WatchlistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update watchlist item note."""
    watchlist_item = db.query(Watchlist).filter(
        Watchlist.id == item_id,
        Watchlist.user_id == current_user.id
    ).first()

    if not watchlist_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found"
        )

    if item.note is not None:
        watchlist_item.note = item.note

    db.commit()
    db.refresh(watchlist_item)
    return watchlist_item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_watchlist(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove stock from watchlist."""
    watchlist_item = db.query(Watchlist).filter(
        Watchlist.id == item_id,
        Watchlist.user_id == current_user.id
    ).first()

    if not watchlist_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watchlist item not found"
        )

    db.delete(watchlist_item)
    db.commit()
    return None
