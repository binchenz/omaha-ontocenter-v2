"""Custom exceptions for Omaha OntoCenter.

This module defines a hierarchy of custom exceptions used throughout the application.
All exceptions inherit from OmahaError and support optional context data.
"""

from typing import Any, Dict, Optional


class OmahaError(Exception):
    """Base exception for all Omaha OntoCenter errors.

    All custom exceptions in the application inherit from this base class.
    Supports optional context data for additional error information.

    Args:
        message: Human-readable error message
        context: Optional dictionary containing additional error context

    Attributes:
        context: Dictionary containing additional error context
    """

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """Initialize OmahaError with message and optional context."""
        super().__init__(message)
        self.context = context or {}


# Configuration Exceptions


class ConfigError(OmahaError):
    """Base exception for configuration-related errors.

    Raised when there are issues with application configuration.
    """

    pass


class ConfigValidationError(ConfigError):
    """Exception raised when configuration validation fails.

    Raised when configuration values do not meet validation requirements.
    """

    pass


class ConfigLoadError(ConfigError):
    """Exception raised when configuration cannot be loaded.

    Raised when configuration files cannot be read or parsed.
    """

    pass


# Data Source Exceptions


class DataSourceError(OmahaError):
    """Base exception for data source-related errors.

    Raised when there are issues accessing or querying data sources.
    """

    pass


class DatabaseConnectionError(DataSourceError):
    """Exception raised when database connection fails.

    Raised when unable to establish or maintain connection to data source.
    """

    pass


class QueryError(DataSourceError):
    """Exception raised when query execution fails.

    Raised when SQL queries fail to execute properly.
    """

    pass


class QueryTimeoutError(QueryError):
    """Exception raised when query execution times out.

    Raised when a query takes longer than the configured timeout period.
    """

    pass


# Ontology Exceptions


class OntologyError(OmahaError):
    """Base exception for ontology-related errors.

    Raised when there are issues with ontology processing or validation.
    """

    pass


class OntologyValidationError(OntologyError):
    """Exception raised when ontology validation fails.

    Raised when ontology structure or content does not meet requirements.
    """

    pass


class SchemaDiscoveryError(OntologyError):
    """Exception raised when schema discovery fails.

    Raised when unable to discover or analyze database schema.
    """

    pass


# Agent Exceptions


class AgentError(OmahaError):
    """Base exception for agent-related errors.

    Raised when there are issues with agent execution or processing.
    """

    pass


class LLMError(AgentError):
    """Exception raised when LLM API calls fail.

    Raised when language model API calls encounter errors.
    """

    pass


class SQLGenerationError(AgentError):
    """Exception raised when SQL generation fails.

    Raised when the agent cannot generate valid SQL from natural language.
    """

    pass


class SQLValidationError(AgentError):
    """Exception raised when SQL validation fails.

    Raised when generated SQL does not pass validation checks.
    """

    pass


# Security Exceptions


class SecurityError(OmahaError):
    """Base exception for security-related errors.

    Raised when security violations are detected.
    """

    pass


class SQLInjectionError(SecurityError):
    """Exception raised when SQL injection is detected.

    Raised when input contains patterns that could indicate SQL injection attempts.
    """

    pass
