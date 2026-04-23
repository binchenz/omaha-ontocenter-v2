"""Tests for pipeline scheduler."""
import pytest
from unittest.mock import patch, MagicMock
from app.services.scheduler import PipelineScheduler, _execute_pipeline


class TestPipelineScheduler:
    def test_start_loads_active_pipelines(self):
        sched = PipelineScheduler()
        mock_pipeline = MagicMock()
        mock_pipeline.id = 1
        mock_pipeline.schedule = "0 * * * *"
        mock_pipeline.status = "active"

        with patch("app.services.scheduler.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.all.return_value = [mock_pipeline]

            sched.start()
            job = sched._scheduler.get_job("pipeline_1")
            assert job is not None
            sched.stop()

    def test_add_pipeline_registers_job(self):
        sched = PipelineScheduler()
        sched._scheduler.start()
        sched.add_pipeline(42, "*/5 * * * *")
        job = sched._scheduler.get_job("pipeline_42")
        assert job is not None
        sched.stop()

    def test_remove_pipeline_removes_job(self):
        sched = PipelineScheduler()
        sched._scheduler.start()
        sched.add_pipeline(42, "*/5 * * * *")
        sched.remove_pipeline(42)
        job = sched._scheduler.get_job("pipeline_42")
        assert job is None
        sched.stop()

    def test_remove_nonexistent_pipeline_is_noop(self):
        sched = PipelineScheduler()
        sched._scheduler.start()
        sched.remove_pipeline(999)
        sched.stop()

    def test_sync_pipeline_updates_job(self):
        sched = PipelineScheduler()
        sched._scheduler.start()
        sched.add_pipeline(10, "0 * * * *")

        mock_pipeline = MagicMock()
        mock_pipeline.id = 10
        mock_pipeline.schedule = "*/30 * * * *"
        mock_pipeline.status = "active"

        with patch("app.services.scheduler.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = mock_pipeline

            sched.sync_pipeline(10)
            job = sched._scheduler.get_job("pipeline_10")
            assert job is not None
        sched.stop()

    def test_sync_paused_pipeline_removes_job(self):
        sched = PipelineScheduler()
        sched._scheduler.start()
        sched.add_pipeline(10, "0 * * * *")

        mock_pipeline = MagicMock()
        mock_pipeline.id = 10
        mock_pipeline.status = "paused"

        with patch("app.services.scheduler.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = mock_pipeline

            sched.sync_pipeline(10)
            job = sched._scheduler.get_job("pipeline_10")
            assert job is None
        sched.stop()

    def test_invalid_cron_does_not_crash(self):
        sched = PipelineScheduler()
        sched._scheduler.start()
        sched.add_pipeline(99, "not a cron")
        job = sched._scheduler.get_job("pipeline_99")
        assert job is None
        sched.stop()


class TestExecutePipeline:
    def test_execute_skips_inactive_pipeline(self):
        mock_pipeline = MagicMock()
        mock_pipeline.status = "paused"

        with patch("app.services.scheduler.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = mock_pipeline

            _execute_pipeline(1)
            # Should not call run_pipeline

    def test_execute_skips_missing_pipeline(self):
        with patch("app.services.scheduler.SessionLocal") as mock_session_cls:
            mock_db = MagicMock()
            mock_session_cls.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            _execute_pipeline(999)
