"""CLI commands for Omaha OntoCenter."""

from omaha.cli.commands.config import config_group
from omaha.cli.commands.ontology import ontology_group
from omaha.cli.commands.query import query_command

__all__ = ["config_group", "ontology_group", "query_command"]
