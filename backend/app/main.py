"""
FastAPI application entry point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import api_router
from app.api.auth import public_auth
from app.api.legacy.financial import public_query
from app import models as _models  # noqa: F401 — registers all ORM classes with Base.metadata
from app.services.platform.scheduler import scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.stop()


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
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
