from typing import Annotated, Literal

from fastapi import Depends, Query
from pydantic import BaseModel

from app.database import get_db as _get_db

# Re-export for convenience
get_db = _get_db


# ---------------------------------------------------------------------------
# Shared FastAPI dependencies
# ---------------------------------------------------------------------------


def _tenant_id_dep(
    tenant_id: Annotated[
        str, Query(description="Tenant isolation scope")
    ] = "default",
) -> str:
    """Resolve the tenant scope for a request.

    Wrapping in a `Depends` factory keeps the default value (and any future
    auth-derived override) in one place, while letting endpoints accept it
    with the same `?tenant_id=...` query semantics as before.
    """
    return tenant_id


# Tenant isolation scope. Endpoints declare `tenant_id: TenantId` — equivalent
# to the previous `tenant_id: str = "default"` but sourced from one place.
TenantId = Annotated[str, Depends(_tenant_id_dep)]


class Pagination(BaseModel):
    """Resolved pagination params used by list endpoints."""

    limit: int = 100
    order: Literal["asc", "desc"] = "desc"


def pagination(
    limit: Annotated[int, Query(ge=1, le=500, description="Max rows to return")] = 100,
    order: Annotated[
        Literal["asc", "desc"], Query(description="Sort direction")
    ] = "desc",
) -> Pagination:
    """Dependency factory for list endpoints — preserves existing 422 behavior
    on invalid `limit`/`order` values via the Query constraints above."""
    return Pagination(limit=limit, order=order)
