"""Pipeline runner — executes a pipeline job: fetch from source, write to local SQLite."""
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.models.pipeline import Pipeline
from app.services.omaha import omaha_service
from app.connectors.csv_connector import CSVConnector

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")


def run_pipeline(pipeline: Pipeline, config_yaml: str, db: Session) -> dict:
    """Execute a pipeline: query source, write rows to local SQLite, update pipeline status."""
    pipeline.last_run_status = "running"
    pipeline.last_run_at = datetime.now(timezone.utc)
    db.commit()

    try:
        result = omaha_service.query_objects(
            config_yaml=config_yaml,
            object_type=pipeline.object_type,
            selected_columns=None,
            filters=pipeline.filters or [],
            limit=None,
        )

        if not result.get("success"):
            raise RuntimeError(result.get("error", "Query failed"))

        rows = result.get("data", [])
        _write_to_local(pipeline, rows)

        pipeline.last_run_status = "success"
        pipeline.last_run_rows = len(rows)
        pipeline.last_error = None
        db.commit()

        return {"success": True, "rows": len(rows)}

    except Exception as e:
        pipeline.last_run_status = "error"
        pipeline.last_error = str(e)
        db.commit()
        return {"success": False, "error": str(e)}


def _write_to_local(pipeline: Pipeline, rows: list[dict]) -> None:
    """Write rows to the project's local imported.db SQLite database."""
    if not rows:
        return

    project_data_dir = os.path.join(DATA_DIR, str(pipeline.project_id))
    os.makedirs(project_data_dir, exist_ok=True)
    db_path = os.path.join(project_data_dir, "imported.db")

    import pandas as pd
    df = pd.DataFrame(rows)
    engine = create_engine(f"sqlite:///{db_path}")
    df.to_sql(pipeline.target_table, engine, if_exists="replace", index=False)
    engine.dispose()
