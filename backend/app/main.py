"""
FastAPI application entry point.
"""
import asyncio
import time
import structlog
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.logging_config import setup_logging
from app.middleware import RequestLoggingMiddleware
from app.config import settings
from app.api import api_router
from app.api.auth import public_auth
from app.api.legacy.financial import public_query
from app import models as _models  # noqa: F401 — registers all ORM classes with Base.metadata
from app.services.platform.scheduler import scheduler
from app.schemas.error import ErrorResponse
from app.database import get_db

setup_logging()

_start_time = time.time()

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await asyncio.to_thread(scheduler.start)
    yield
    await asyncio.to_thread(scheduler.stop)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", path=request.url.path, method=request.method)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error="Internal Server Error").model_dump(),
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")
app.include_router(public_auth.router, prefix="/api/public/auth", tags=["public-auth"])
app.include_router(public_query.router, prefix="/api/public/v1", tags=["public-query"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }


@app.get("/health")
async def health(db: Session = Depends(get_db)):
    checks = {}

    # Database connectivity
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    # Config presence checks
    checks["tushare_configured"] = bool(settings.TUSHARE_TOKEN)
    checks["llm_configured"] = bool(settings.DEEPSEEK_API_KEY or settings.OPENAI_API_KEY)

    db_ok = checks["database"] == "ok"
    status = "healthy" if db_ok else "unhealthy"
    status_code = 200 if db_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status,
            "checks": checks,
            "version": settings.APP_VERSION,
            "uptime_seconds": round(time.time() - _start_time),
        },
    )
