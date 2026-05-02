"""Wipe a tenant's ontology, datasource, and Delta-table state.

Usage:
    PYTHONPATH=. python scripts/cleanup_tenant.py --tenant default
    PYTHONPATH=. python scripts/cleanup_tenant.py --tenant default --confirm

Behaviour:
    * Without --confirm: dry-run (counts only, no mutations).
    * With --confirm:
        - Deletes ontologies (+ objects/properties/links/functions) for the tenant.
        - Deletes datasources (+ datasets) for the tenant.
        - Removes the Delta-storage directory referenced by each deleted dataset's
          ``delta_path``.

Safety:
    * Refuses empty / wildcard tenant ids.
    * Uses a single transaction; rolls back on error before touching the
      filesystem.

Note: SQLAlchemy models in ``app/models/ontology.py`` and
``app/models/datasource.py`` do not declare cascade rules, so we explicitly
remove children-before-parents.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

# Ensure ``app`` package is importable when run from anywhere.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.models import (  # noqa: E402
    DataSource,
    Dataset,
    Ontology,
    OntologyFunction,
    OntologyLink,
    OntologyObject,
    OntologyProperty,
)


def _sync_url(url: str) -> str:
    """Convert async SQLAlchemy URL to its sync equivalent, anchoring any
    relative SQLite path at the project root so the script works from any CWD."""
    sync = (
        url.replace("sqlite+aiosqlite", "sqlite")
        .replace("postgresql+asyncpg", "postgresql+psycopg2")
        .replace("mysql+aiomysql", "mysql+pymysql")
    )
    # Rewrite ``sqlite:///./foo.db`` or ``sqlite:///foo.db`` into an absolute path.
    prefix = "sqlite:///"
    if sync.startswith(prefix):
        db_path = sync[len(prefix):]
        p = Path(db_path)
        if not p.is_absolute():
            p = (ROOT / p).resolve()
        sync = f"{prefix}{p}"
    return sync


def _resolve_delta_path(raw: str) -> Path:
    """Return absolute path for a dataset's ``delta_path`` (relative to project root)."""
    p = Path(raw)
    if not p.is_absolute():
        p = (ROOT / p).resolve()
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant", required=True, help="Tenant id to wipe (e.g. 'default').")
    ap.add_argument("--confirm", action="store_true", help="Actually perform deletions.")
    args = ap.parse_args()

    tenant = (args.tenant or "").strip()
    if not tenant or tenant in {"*", "%"}:
        print("ERROR: refusing to run with empty/wildcard tenant id.", file=sys.stderr)
        return 2

    engine = create_engine(_sync_url(settings.database_url), future=True)
    delta_paths_to_remove: list[Path] = []

    with Session(engine) as db:
        ontology_ids = [
            row[0]
            for row in db.execute(
                select(Ontology.id).where(Ontology.tenant_id == tenant)
            ).all()
        ]
        datasource_ids = [
            row[0]
            for row in db.execute(
                select(DataSource.id).where(DataSource.tenant_id == tenant)
            ).all()
        ]

        # Pre-compute object ids so we can scope property deletes.
        object_ids: list[str] = []
        if ontology_ids:
            object_ids = [
                row[0]
                for row in db.execute(
                    select(OntologyObject.id).where(
                        OntologyObject.ontology_id.in_(ontology_ids)
                    )
                ).all()
            ]

        # Datasets are scoped by tenant_id directly.
        dataset_rows = (
            db.execute(
                select(Dataset.id, Dataset.delta_path).where(Dataset.tenant_id == tenant)
            )
            .all()
        )
        delta_paths_to_remove = [_resolve_delta_path(row.delta_path) for row in dataset_rows]

        print(
            f"Tenant '{tenant}': "
            f"{len(ontology_ids)} ontologies, "
            f"{len(object_ids)} objects, "
            f"{len(datasource_ids)} datasources, "
            f"{len(dataset_rows)} datasets, "
            f"{len(delta_paths_to_remove)} Delta dirs."
        )

        if not args.confirm:
            print("Dry-run only. Re-run with --confirm to delete.")
            return 0

        print(
            f"*** --confirm set: deleting tenant '{args.tenant}' state now ***",
            file=sys.stderr,
        )

        # --- Delete in child-first order to satisfy FK constraints. ---
        if object_ids:
            db.execute(
                delete(OntologyProperty).where(
                    OntologyProperty.object_id.in_(object_ids)
                )
            )
        if ontology_ids:
            db.execute(
                delete(OntologyObject).where(
                    OntologyObject.ontology_id.in_(ontology_ids)
                )
            )
            db.execute(
                delete(OntologyLink).where(OntologyLink.ontology_id.in_(ontology_ids))
            )
            db.execute(
                delete(OntologyFunction).where(
                    OntologyFunction.ontology_id.in_(ontology_ids)
                )
            )
            db.execute(delete(Ontology).where(Ontology.id.in_(ontology_ids)))

        if datasource_ids:
            db.execute(
                delete(Dataset).where(Dataset.datasource_id.in_(datasource_ids))
            )
            db.execute(delete(DataSource).where(DataSource.id.in_(datasource_ids)))

        # Also wipe any datasets that were tenant-scoped but somehow lacked a
        # parent datasource (defensive).
        db.execute(delete(Dataset).where(Dataset.tenant_id == tenant))

        db.commit()
        print(
            f"DB: deleted {len(ontology_ids)} ontologies, "
            f"{len(object_ids)} objects, "
            f"{len(datasource_ids)} datasources, "
            f"{len(dataset_rows)} datasets."
        )

    # --- Filesystem cleanup (only after DB commit succeeded). ---
    nuked = 0
    delta_root_default = (ROOT / "data" / "delta").resolve()
    for path in delta_paths_to_remove:
        # Defensive: refuse to delete anything outside data/delta.
        try:
            path.relative_to(delta_root_default)
        except ValueError:
            print(f"  skip (outside delta root): {path}")
            continue
        if path.exists():
            shutil.rmtree(path)
            nuked += 1
    print(f"Filesystem: removed {nuked} Delta directories under {delta_root_default}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
