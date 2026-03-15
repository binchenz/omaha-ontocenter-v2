"""Configuration loader with environment variable substitution."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml
from pydantic import ValidationError

from omaha.core.config.schema import RootConfig
from omaha.utils.exceptions import ConfigLoadError, ConfigValidationError

# Pattern to match ${VAR_NAME} in strings
# NOTE: This pattern intentionally matches only uppercase variable names (following shell convention).
# Lowercase patterns like ${var} will NOT be substituted and will fail validation later.
ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def substitute_env_vars(config_dict: Dict[str, Any], path: str = "") -> Dict[str, Any]:
    """Recursively substitute environment variables in configuration dictionary.

    Args:
        config_dict: Configuration dictionary potentially containing ${VAR_NAME} patterns
        path: Current path in the config (for error messages)

    Returns:
        Configuration dictionary with environment variables substituted

    Raises:
        ConfigLoadError: If a referenced environment variable is not found
    """
    def _substitute_value(value: Any, current_path: str) -> Any:
        """Recursively substitute environment variables in a value."""
        if isinstance(value, str):
            # Find all environment variable references in the string
            matches = ENV_VAR_PATTERN.findall(value)
            for var_name in matches:
                if var_name not in os.environ:
                    raise ConfigLoadError(
                        f"Environment variable '{var_name}' not found (referenced at config path: {current_path})",
                        context={"variable": var_name, "value": value, "config_path": current_path}
                    )
                # Replace ${VAR_NAME} with the environment variable value
                value = value.replace(f"${{{var_name}}}", os.environ[var_name])
            return value
        elif isinstance(value, dict):
            return {k: _substitute_value(v, f"{current_path}.{k}" if current_path else k) for k, v in value.items()}
        elif isinstance(value, list):
            return [_substitute_value(item, f"{current_path}[{i}]") for i, item in enumerate(value)]
        else:
            # Return non-string, non-dict, non-list values as-is
            return value

    return _substitute_value(config_dict, path)


def load_config(file_path: str) -> RootConfig:
    """Load and validate configuration from YAML file.

    Args:
        file_path: Path to YAML configuration file

    Returns:
        Validated RootConfig instance

    Raises:
        ConfigLoadError: If file cannot be read or parsed
        ConfigValidationError: If configuration validation fails
    """
    # Check if file exists
    config_path = Path(file_path)
    if not config_path.exists():
        raise ConfigLoadError(
            f"Configuration file not found: {file_path}",
            context={"file_path": file_path}
        )

    # Check file size (prevent DoS from huge files)
    file_size = config_path.stat().st_size
    max_size = 10 * 1024 * 1024  # 10MB
    if file_size > max_size:
        raise ConfigLoadError(
            f"Configuration file too large: {file_size} bytes (max: {max_size} bytes)",
            context={"file_path": file_path, "file_size": file_size, "max_size": max_size}
        )

    # Read and parse YAML file
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigLoadError(
            f"Failed to parse YAML configuration: {e}",
            context={"file_path": file_path, "error": str(e)}
        )
    except Exception as e:
        raise ConfigLoadError(
            f"Failed to read configuration file: {e}",
            context={"file_path": file_path, "error": str(e)}
        )

    # Ensure we got a dictionary
    if not isinstance(config_data, dict):
        raise ConfigLoadError(
            "Configuration file must contain a YAML dictionary",
            context={"file_path": file_path, "type": type(config_data).__name__}
        )

    # Substitute environment variables
    try:
        config_data = substitute_env_vars(config_data, file_path)
    except ConfigLoadError:
        # Re-raise ConfigLoadError as-is
        raise

    # Validate configuration with Pydantic schema
    try:
        config = RootConfig(**config_data)
    except ValidationError as e:
        raise ConfigValidationError(
            f"Configuration validation failed: {e}",
            context={"file_path": file_path, "errors": e.errors()}
        )

    return config
