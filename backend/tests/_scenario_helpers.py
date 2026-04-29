"""Shared helpers for verify_*.py scenario scripts.

These scripts run real LLM calls against ChatServiceV2 to validate end-to-end
agent behaviour. They are not pytest tests (don't start with `test_`); they
print a transcript and exit zero on success.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_BACKEND_ROOT.parent / ".env")


# ─── DB / project bootstrap ──────────────────────────────────────────────────

def setup_db(
    *,
    username: str = "demo",
    email: str = "demo@test.com",
    project_name: str = "Demo Project",
    project_description: str | None = None,
):
    """Create an in-memory SQLite DB, seed tenant + user + project, return
    (db, project, user). Project starts in setup_stage='modeling' so callers
    can drive the agent through the modeling skill immediately.
    """
    from app.database import Base
    from app.models.auth.tenant import Tenant
    from app.models.auth.user import User
    from app.models.project.project import Project
    from app.core.security import get_password_hash
    import app.models  # noqa: F401 — registers all ORM classes with Base.metadata

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    tenant = Tenant(name="demo")
    db.add(tenant)
    db.commit()

    user = User(
        username=username,
        email=email,
        hashed_password=get_password_hash("test"),
        tenant_id=tenant.id,
    )
    db.add(user)
    db.commit()

    project = Project(
        name=project_name,
        description=project_description,
        owner_id=user.id,
        tenant_id=tenant.id,
        setup_stage="modeling",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return db, project, user


# ─── Chat ────────────────────────────────────────────────────────────────────

async def chat(project, db, session_id: int, message: str,
               uploaded_tables: dict | None = None) -> dict[str, Any]:
    """Run one chat turn through ChatServiceV2 with optional uploaded_tables."""
    from app.services.agent.chat_service import ChatServiceV2

    svc = ChatServiceV2(project=project, db=db)
    return await svc.send_message(
        session_id=session_id,
        user_message=message,
        uploaded_tables=uploaded_tables,
    )


# ─── Pretty printing ─────────────────────────────────────────────────────────

_RENDER_MAX_CHARS = 900


def banner(text: str) -> None:
    print(f"\n{'═' * 78}\n  {text}\n{'═' * 78}")


def render(role: str, text: str, tools: list | None = None,
           max_chars: int = _RENDER_MAX_CHARS) -> None:
    icon = "👤" if role == "user" else "🤖"
    print(f"\n{icon} {role.upper()}:")
    truncated = text[:max_chars] if max_chars else text
    for line in truncated.split("\n"):
        print(f"   {line}")
    if max_chars and len(text) > max_chars:
        print(f"   ... ({len(text)} chars total, truncated)")
    if tools:
        names = [t.get("name", "?") for t in tools]
        print(f"\n   🔧 工具调用 ({len(names)}): {' → '.join(names)}")


# ─── Mock data → SQLite + omaha_config ───────────────────────────────────────

def materialize_to_sqlite(uploaded: dict[str, pd.DataFrame], path: str) -> None:
    """Write each DataFrame in `uploaded` as a table named after its key."""
    conn = sqlite3.connect(path)
    try:
        for name, df in uploaded.items():
            df.to_sql(name, conn, if_exists="replace", index=False)
    finally:
        conn.close()


def build_omaha_yaml(db, tenant_id: int, db_path: str) -> str:
    """Build a minimal omaha_config YAML from the persisted ontology, pointing
    its `upload` datasource at db_path. Used after confirm_ontology has run."""
    from app.services.ontology.store import OntologyStore

    ontology = OntologyStore(db).get_full_ontology(tenant_id)
    objects_yaml = [
        {
            "name": obj["name"],
            "datasource": "upload",
            "source_entity": obj["source_entity"],
            "properties": [
                {"name": p["name"], "type": p.get("type") or "string"}
                for p in obj["properties"]
            ],
        }
        for obj in ontology["objects"]
    ]
    return yaml.safe_dump({
        "datasources": [
            {"id": "upload", "type": "sqlite", "connection": {"database": db_path}}
        ],
        "ontology": {"objects": objects_yaml},
    }, allow_unicode=True, sort_keys=False)


class TempSqliteDB:
    """Context manager: materialize uploaded DataFrames to a temp SQLite file
    that's always cleaned up, even on exception."""

    def __init__(self, uploaded: dict[str, pd.DataFrame]):
        self.uploaded = uploaded
        self.path: str | None = None

    def __enter__(self) -> str:
        f = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        f.close()
        self.path = f.name
        materialize_to_sqlite(self.uploaded, self.path)
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.path:
            try:
                os.unlink(self.path)
            except FileNotFoundError:
                pass


__all__ = [
    "setup_db",
    "chat",
    "banner",
    "render",
    "materialize_to_sqlite",
    "build_omaha_yaml",
    "TempSqliteDB",
]
