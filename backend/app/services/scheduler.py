"""Backward-compat shim. Real implementation lives at app.services.platform.scheduler."""
from app.services.platform.scheduler import (  # noqa: F401
    JOB_PREFIX,
    PipelineScheduler,
    scheduler,
    _execute_pipeline,
    SessionLocal,
    Pipeline,
    Project,
    run_pipeline,
)
