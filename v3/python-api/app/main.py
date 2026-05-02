from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    # H1 follow-up: an empty INTERNAL_API_SECRET silently disables the
    # internal-auth middleware (see `internal_auth` below). That's fine for
    # dev, catastrophic in prod — the Python API would become a public proxy
    # for any tenant's data. Fail fast so the operator can't miss it.
    if not settings.internal_api_secret:
        raise RuntimeError(
            "INTERNAL_API_SECRET must be non-empty in production. "
            "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))' "
            "and set the same value in the Next.js server env."
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


@app.middleware("http")
async def internal_auth(request: Request, call_next):
    """Reject requests that don't carry the shared internal-auth header.

    H1 (HIGH) fix: Python API endpoints accept `tenant_id` from the query
    string with no auth. Anyone with HTTP access could read/delete other
    tenants' data. The Next.js server (which already authenticates the user
    via NextAuth/JWT) injects `X-Internal-Auth: <secret>` on every Python
    call; Python verifies it here before any endpoint runs.

    /health is exempted so k8s liveness/readiness probes still work.
    Empty secret → middleware is a no-op (dev/test convenience). Production
    deployments must set a non-empty `INTERNAL_API_SECRET`.

    This is NOT full multi-tenant auth (P6 territory) — `tenant_id` is still
    trusted from the query string. It just stops Python from being a public
    proxy for tenant data.
    """
    # k8s probes hit /health unauthenticated — keep that path open.
    if request.url.path == "/health":
        return await call_next(request)

    expected = settings.internal_api_secret
    if not expected:
        # Disabled in dev — caller didn't configure a secret.
        return await call_next(request)

    got = request.headers.get("x-internal-auth")
    if got != expected:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    return await call_next(request)


app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(ontology_router)
app.include_router(mcp_router)
app.include_router(mcp_runtime_router)
app.include_router(datasources_router)
