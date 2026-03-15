"""Ontology management commands."""

import sys

import click

from omaha.core.config.loader import load_config
from omaha.core.ontology.engine import OntologyEngine
from omaha.cli.formatters import format_ontology, format_ontology_object
from omaha.utils.exceptions import ConfigLoadError, ConfigValidationError, OntologyError


@click.group(name="ontology")
def ontology_group():
    """Ontology management commands."""
    pass


@ontology_group.command(name="discover")
@click.argument("config_file", type=click.Path(exists=True))
def discover_ontology(config_file):
    """Discover database schema and build ontology."""
    try:
        # Load configuration
        config = load_config(config_file)

        # Build ontology
        engine = OntologyEngine(config)
        ontology = engine.build_ontology()

        # Format and display
        format_ontology(ontology)

    except (ConfigLoadError, ConfigValidationError, OntologyError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@ontology_group.command(name="show")
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--object", "object_name", help="Show specific object")
def show_ontology(config_file, object_name):
    """Display ontology details."""
    try:
        # Load configuration
        config = load_config(config_file)

        # Build ontology
        engine = OntologyEngine(config)
        ontology = engine.build_ontology()

        # Display specific object or all
        if object_name:
            if object_name not in ontology:
                click.echo(f"Error: Object '{object_name}' not found", err=True)
                sys.exit(1)
            format_ontology_object(ontology[object_name])
        else:
            format_ontology(ontology)

    except (ConfigLoadError, ConfigValidationError, OntologyError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
