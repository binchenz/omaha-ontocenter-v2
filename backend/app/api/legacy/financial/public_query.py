"""Public query API endpoints."""
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.auth.user import User
from app.models.chat.public_query_log import PublicQueryLog
from app.models.legacy.financial.watchlist import Watchlist
from app.api.public_deps import verify_api_key
from app.schemas.legacy.financial.public_query import (
    QueryRequest,
    QueryResponse,
    ObjectListResponse,
    ObjectInfo,
    SchemaResponse,
    AggregateRequest,
    AggregateResponse,
    WatchlistAddRequest,
    WatchlistItemResponse,
    WatchlistListResponse,
)
from app.services.legacy.financial.ontology_cache_service import OntologyCacheService
import yaml
import os

router = APIRouter()

RATE_LIMIT = 1000  # queries per hour

# Load ontology config — file lives at backend/app/api/legacy/financial/, repo root is 6 dirnames up
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))))
config_path = os.path.join(_REPO_ROOT, 'configs/financial_stock_analysis.yaml')
with open(config_path, 'r') as f:
    ONTOLOGY_CONFIG = yaml.safe_load(f)

def get_available_objects():
    """Get list of available objects from ontology config."""
    return [obj['name'] for obj in ONTOLOGY_CONFIG['ontology']['objects']]


def check_rate_limit(user: User, db: Session):
    """Check if user has exceeded rate limit."""
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    count = db.query(func.count(PublicQueryLog.id)).filter(
        PublicQueryLog.user_id == user.id,
        PublicQueryLog.created_at >= one_hour_ago
    ).scalar()

    if count >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


@router.get("/objects", response_model=ObjectListResponse)
def list_objects(
    user: User = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """List available objects."""
    # check_rate_limit(user, db)  # Rate limit disabled

    log = PublicQueryLog(
        user_id=user.id,
        query_type="list_objects",
        result_count=1,
        execution_time_ms=0
    )
    db.add(log)
    db.commit()

    objects = [
        ObjectInfo(object_type=obj['name'], description=obj.get('description', ''))
        for obj in ONTOLOGY_CONFIG['ontology']['objects']
    ]
    return ObjectListResponse(objects=objects)


@router.get("/schema/{object_type}", response_model=SchemaResponse)
def get_schema(
    object_type: str,
    user: User = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get object schema."""
    # check_rate_limit(user, db)  # Rate limit disabled

    if object_type not in get_available_objects():
        raise HTTPException(status_code=404, detail="Object type not found")

    cache_service = OntologyCacheService(db)
    schema = cache_service.get_object_schema(object_type)

    log = PublicQueryLog(
        user_id=user.id,
        query_type="get_schema",
        object_type=object_type,
        result_count=1,
        execution_time_ms=0
    )
    db.add(log)
    db.commit()

    return SchemaResponse(**schema)


@router.post("/query", response_model=QueryResponse)
def query_data(
    request: QueryRequest,
    user: User = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Query data with rate limiting."""
    # check_rate_limit(user, db)  # Rate limit disabled

    if request.object_type not in get_available_objects():
        raise HTTPException(status_code=400, detail="Unsupported object type")

    start_time = time.time()
    cache_service = OntologyCacheService(db)
    data = cache_service.query_objects(
        object_type=request.object_type,
        filters=request.filters,
        limit=request.limit,
        offset=request.offset,
        format_output=request.format,
        order_by=request.order_by,
        order=request.order,
        select=request.select
    )
    execution_time_ms = int((time.time() - start_time) * 1000)

    log = PublicQueryLog(
        user_id=user.id,
        query_type="query",
        object_type=request.object_type,
        filters=request.filters,
        result_count=len(data),
        execution_time_ms=execution_time_ms
    )
    db.add(log)
    db.commit()

    return QueryResponse(
        data=data,
        count=len(data),
        limit=request.limit,
        offset=request.offset,
        execution_time_ms=execution_time_ms
    )


@router.post("/aggregate", response_model=AggregateResponse)
def aggregate_data(
    request: AggregateRequest,
    user: User = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Aggregate data with statistical functions."""
    # check_rate_limit(user, db)  # Rate limit disabled

    if request.object_type not in get_available_objects():
        raise HTTPException(status_code=400, detail="Unsupported object type")

    start_time = time.time()
    cache_service = OntologyCacheService(db)
    result = cache_service.aggregate_objects(
        object_type=request.object_type,
        filters=request.filters,
        aggregations=request.aggregations
    )
    execution_time_ms = int((time.time() - start_time) * 1000)

    log = PublicQueryLog(
        user_id=user.id,
        query_type="aggregate",
        object_type=request.object_type,
        filters=request.filters,
        result_count=result["count"],
        execution_time_ms=execution_time_ms
    )
    db.add(log)
    db.commit()

    return AggregateResponse(**result)


@router.get("/watchlist", response_model=WatchlistListResponse)
def get_watchlist(
    user: User = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get user's watchlist."""
    items = db.query(Watchlist).filter(Watchlist.user_id == user.id).all()
    return WatchlistListResponse(
        items=[
            WatchlistItemResponse(
                id=item.id,
                ts_code=item.ts_code,
                note=item.note,
                added_at=item.added_at.isoformat()
            )
            for item in items
        ],
        count=len(items)
    )


@router.post("/watchlist", response_model=WatchlistItemResponse, status_code=201)
def add_watchlist(
    request: WatchlistAddRequest,
    user: User = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Add stock to watchlist."""
    from sqlalchemy.exc import IntegrityError

    item = Watchlist(user_id=user.id, ts_code=request.ts_code, note=request.note)
    db.add(item)
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Stock already in watchlist")

    return WatchlistItemResponse(
        id=item.id,
        ts_code=item.ts_code,
        note=item.note,
        added_at=item.added_at.isoformat()
    )


@router.delete("/watchlist/{item_id}", status_code=204)
def remove_watchlist(
    item_id: int,
    user: User = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Remove stock from watchlist."""
    item = db.query(Watchlist).filter(
        Watchlist.id == item_id,
        Watchlist.user_id == user.id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Watchlist item not found")

    db.delete(item)
    db.commit()
    return None
