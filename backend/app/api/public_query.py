"""Public query API endpoints."""
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models.user import User
from app.models.public_query_log import PublicQueryLog
from app.api.public_deps import verify_api_key
from app.schemas.public_query import (
    QueryRequest,
    QueryResponse,
    ObjectListResponse,
    ObjectInfo,
    SchemaResponse,
)
from app.services.cache_service import CacheService

router = APIRouter()

RATE_LIMIT = 100  # queries per hour


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
    check_rate_limit(user, db)

    log = PublicQueryLog(
        user_id=user.id,
        query_type="list_objects",
        result_count=1,
        execution_time_ms=0
    )
    db.add(log)
    db.commit()

    return ObjectListResponse(
        objects=[
            ObjectInfo(object_type="Stock", description="Stock information")
        ]
    )


@router.get("/schema/{object_type}", response_model=SchemaResponse)
def get_schema(
    object_type: str,
    user: User = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """Get object schema."""
    check_rate_limit(user, db)

    if object_type != "Stock":
        raise HTTPException(status_code=404, detail="Object type not found")

    cache_service = CacheService(db)
    schema = cache_service.get_stock_schema()

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
    check_rate_limit(user, db)

    if request.object_type != "Stock":
        raise HTTPException(status_code=400, detail="Unsupported object type")

    start_time = time.time()
    cache_service = CacheService(db)
    data = cache_service.query_stocks(
        filters=request.filters,
        limit=request.limit,
        offset=request.offset
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
        offset=request.offset
    )
