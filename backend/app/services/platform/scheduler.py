"""Pipeline scheduler — runs active pipelines on their cron schedule using APScheduler."""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor

from app.database import SessionLocal
from app.models.pipeline.pipeline import Pipeline
from app.models.project.project import Project
from app.services.platform.pipeline_runner import run_pipeline

logger = logging.getLogger(__name__)

JOB_PREFIX = "pipeline_"


class PipelineScheduler:
    def __init__(self):
        self._scheduler = BackgroundScheduler(
            executors={"default": ThreadPoolExecutor(max_workers=5)},
            job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 300},
        )

    def start(self):
        db = SessionLocal()
        try:
            pipelines = db.query(Pipeline).filter(Pipeline.status == "active").all()
            for p in pipelines:
                self._add_job(p.id, p.schedule)
            logger.info(f"Scheduler started with {len(pipelines)} active pipelines")
        except Exception as e:
            logger.warning(f"Scheduler: could not load pipelines ({e}), starting empty")
        finally:
            db.close()
        self._scheduler.start()

    def stop(self):
        self._scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    def add_pipeline(self, pipeline_id: int, schedule: str):
        self._add_job(pipeline_id, schedule)

    def remove_pipeline(self, pipeline_id: int):
        job_id = f"{JOB_PREFIX}{pipeline_id}"
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

    def sync_pipeline(self, pipeline_id: int):
        db = SessionLocal()
        try:
            p = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
            if not p:
                self.remove_pipeline(pipeline_id)
                return
            job_id = f"{JOB_PREFIX}{pipeline_id}"
            if p.status == "active":
                try:
                    trigger = CronTrigger.from_crontab(p.schedule)
                    if self._scheduler.get_job(job_id):
                        self._scheduler.reschedule_job(job_id, trigger=trigger)
                    else:
                        self._add_job(p.id, p.schedule)
                except Exception as e:
                    logger.error(f"Failed to sync pipeline {pipeline_id}: {e}")
            else:
                self.remove_pipeline(pipeline_id)
        finally:
            db.close()

    def _add_job(self, pipeline_id: int, schedule: str):
        job_id = f"{JOB_PREFIX}{pipeline_id}"
        try:
            trigger = CronTrigger.from_crontab(schedule)
            self._scheduler.add_job(
                _execute_pipeline,
                trigger=trigger,
                id=job_id,
                args=[pipeline_id],
                replace_existing=True,
            )
        except Exception as e:
            logger.error(f"Failed to schedule pipeline {pipeline_id}: {e}")


def _execute_pipeline(pipeline_id: int):
    """Job function — runs in a thread pool thread with its own DB session."""
    db = SessionLocal()
    pipeline = None
    try:
        pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        if not pipeline or pipeline.status != "active":
            return

        project = db.query(Project).filter(Project.id == pipeline.project_id).first()
        if not project or not project.omaha_config:
            logger.warning(f"Pipeline {pipeline_id}: project has no config")
            return

        config_yaml = project.omaha_config
        if isinstance(config_yaml, bytes):
            config_yaml = config_yaml.decode("utf-8")

        result = run_pipeline(pipeline, config_yaml, db, triggered_by="scheduler")
        if result.get("success"):
            logger.info(f"Pipeline {pipeline_id} completed: {result.get('rows')} rows")
        else:
            logger.error(f"Pipeline {pipeline_id} failed: {result.get('error')}")
    except Exception as e:
        logger.exception("Pipeline %s failed with unhandled exception", pipeline_id)
        if pipeline:
            try:
                pipeline.last_run_status = "error"
                pipeline.last_error = str(e)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Failed to update pipeline %s error status", pipeline_id)
    finally:
        db.close()


scheduler = PipelineScheduler()
