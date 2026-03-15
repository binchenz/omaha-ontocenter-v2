"""Main CLI entry point."""

import click

from omaha.cli.commands.config import config_group
from omaha.cli.commands.ontology import ontology_group
from omaha.cli.commands.query import query_command


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Omaha OntoCenter - Configuration-driven pricing analysis platform."""
    pass


# Register command groups
cli.add_command(config_group)
cli.add_command(ontology_group)
cli.add_command(query_command)


if __name__ == "__main__":
    cli()
