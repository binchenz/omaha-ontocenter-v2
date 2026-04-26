"""New canonical path. Actual implementation lives in app.services.scheduler for backward compat."""
from app.services.scheduler import JOB_PREFIX, PipelineScheduler, scheduler, _execute_pipeline, SessionLocal  # noqa: F401
