import structlog
from app.logging_config import setup_logging


def test_setup_logging_configures_structlog():
    setup_logging()
    logger = structlog.get_logger()
    assert logger is not None
    # Verify structlog is configured (won't raise)
    logger.info("test_message", key="value")
