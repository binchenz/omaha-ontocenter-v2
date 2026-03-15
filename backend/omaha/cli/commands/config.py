"""Configuration management commands."""

import sys

import click

from omaha.core.config.loader import load_config
from omaha.core.config.validator import validate_config
from omaha.cli.formatters import format_validation_result, format_config
from omaha.utils.exceptions import ConfigLoadError, ConfigValidationError


@click.group(name="config")
def config_group():
    """Configuration management commands."""
    pass


@config_group.command(name="validate")
@click.argument("config_file", type=click.Path(exists=True))
def validate_config_cmd(config_file):
    """Validate a configuration file."""
    try:
        # Load configuration
        config = load_config(config_file)

        # Validate against database
        result = validate_config(config)

        # Format and display results
        format_validation_result(result)

        # Exit with appropriate code
        if not result.is_valid:
            sys.exit(1)

    except (ConfigLoadError, ConfigValidationError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@config_group.command(name="show")
@click.argument("config_file", type=click.Path(exists=True))
def show_config(config_file):
    """Display configuration details."""
    try:
        # Load configuration
        config = load_config(config_file)

        # Format and display
        format_config(config)

    except (ConfigLoadError, ConfigValidationError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
