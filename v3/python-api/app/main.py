from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.ontology import router as ontology_router
from app.api.mcp import router as mcp_router
from app.api.mcp_runtime import router as mcp_runtime_router
from app.api.datasources import router as datasources_router


def _validate_production_secrets() -> None:
    """Refuse to start with default weak secrets in production environments."""
    import os
    env = os.environ.get("ENV", "development").lower()
    if env not in ("production", "prod"):
        return
    if settings.secret_key in ("dev-secret-change-in-production", "change-me-in-production", ""):
        raise RuntimeError(
            "SECRET_KEY is still set to a default value. Set a strong random secret via env."
        )


_validate_production_secrets()

app = FastAPI(title="OntoCenter v3 Python API", version="0.1.0")

_allowed_origins = [
    o.strip() for o in (settings.cors_origins or "http://localhost:3000,http://127.0.0.1:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(ontology_router)
app.include_router(mcp_router)
app.include_router(mcp_runtime_router)
app.include_router(datasources_router)
