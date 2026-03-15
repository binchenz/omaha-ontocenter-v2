"""Query command for natural language queries."""

import sys

import click

from omaha.core.config.loader import load_config
from omaha.core.ontology.engine import OntologyEngine
from omaha.core.agent.graph import run_query
from omaha.cli.formatters import format_query_result
from omaha.utils.exceptions import ConfigLoadError, ConfigValidationError, OntologyError, AgentError


@click.command(name="query")
@click.argument("config_file", type=click.Path(exists=True))
@click.argument("question")
@click.option("--llm-provider", default="openai", help="LLM provider (openai, anthropic, or deepseek)")
def query_command(config_file, question, llm_provider):
    """Execute a natural language query."""
    try:
        # Load configuration
        config = load_config(config_file)

        # Build ontology
        engine = OntologyEngine(config)
        ontology = engine.build_ontology()

        # Run query through agent
        result = run_query(
            question=question,
            config=config,
            ontology=ontology,
            llm_provider=llm_provider
        )

        # Format and display results
        format_query_result(result)

    except (ConfigLoadError, ConfigValidationError, OntologyError, AgentError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)
