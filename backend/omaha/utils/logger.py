"""Structured logging setup for Omaha OntoCenter.

This module provides structured logging using structlog with support for:
- JSON output for production
- Pretty console output for development
- Trace IDs in all logs
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)

Important: Call configure_logging() once at application startup before creating loggers.
"""

import logging
import os
import sys
import uuid
from typing import Any

import structlog


def add_trace_id(logger: Any, method_name: str, event_dict: dict) -> dict:
    """Add trace_id to log entries.

    Checks if trace_id exists in the context first. If not present,
    generates a new UUID. To use a specific trace_id, bind it to the
    logger context:

        logger = logger.bind(trace_id="your-trace-id")

    Or set it in structlog's context vars before logging.

    Args:
        logger: Logger instance
        method_name: Name of the logging method being called
        event_dict: Dictionary containing log event data

    Returns:
        Updated event_dict with trace_id
    """
    if "trace_id" not in event_dict:
        event_dict["trace_id"] = str(uuid.uuid4())
    return event_dict


def configure_logging(environment: str = "development", level: str = "INFO") -> None:
    """Configure structlog for the application.

    This function should be called once at application startup to configure
    the logging system. After calling this, use setup_logger() to create
    individual logger instances.

    Args:
        environment: Environment name (development, production, etc.)
        level: Default log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Raises:
        ValueError: If invalid log level is provided
    """
    # Validate log level
    level_upper = level.upper()
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level_upper not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")

    # Convert string level to logging constant
    numeric_level = getattr(logging, level_upper)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=numeric_level,
    )

    # Determine if we're in development or production
    is_dev = environment.lower() in ("development", "dev", "local")

    # Shared processors for all environments
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_trace_id,
    ]

    # Configure processors based on environment
    if is_dev:
        # Development: Pretty console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.plain_traceback,
            )
        ]
    else:
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog (should only be called once at startup)
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def setup_logger(name: str, level: str = "INFO") -> Any:
    """Set up and return a configured structlog logger.

    Returns a logger instance. Note: configure_logging() should be called
    once at application startup before using this function.

    Args:
        name: Logger name (typically module name)
        level: Log level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO.

    Returns:
        Configured structlog logger instance

    Raises:
        ValueError: If invalid log level is provided

    Example:
        >>> # At application startup:
        >>> configure_logging(environment="development")
        >>>
        >>> # In your modules:
        >>> logger = setup_logger(__name__)
        >>> logger.info("User logged in", user_id=123)
        >>> logger.error("Database error", error="Connection timeout")
    """
    # Validate log level
    level_upper = level.upper()
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level_upper not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")

    # For backward compatibility, configure logging if not already configured
    # In production, configure_logging() should be called explicitly at startup
    if not structlog.is_configured():
        environment = os.getenv("ENVIRONMENT", "development")
        configure_logging(environment=environment, level=level)

    # Return logger instance
    return structlog.get_logger(name)
