"""Output formatting with Rich."""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import box

from omaha.core.config.validator import ValidationResult
from omaha.core.config.schema import RootConfig
from omaha.core.ontology.models import OntologyObject

console = Console()


def format_validation_result(result: ValidationResult) -> None:
    """Format validation result with Rich.

    Args:
        result: ValidationResult to format
    """
    if result.is_valid:
        console.print("[green]✓ Configuration is valid[/green]")
    else:
        console.print("[red]✗ Configuration validation failed[/red]")

    # Display errors
    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in result.errors:
            console.print(f"  • {error}")

    # Display warnings
    if result.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  • {warning}")


def format_config(config: RootConfig) -> None:
    """Format configuration with Rich.

    Args:
        config: RootConfig to format
    """
    # Client info
    console.print(Panel(
        f"[bold]{config.client.name}[/bold]\n"
        f"Industry: {config.client.industry}",
        title="Client Information",
        border_style="blue"
    ))

    # Datasources
    if config.datasources:
        table = Table(title="Datasources", box=box.ROUNDED)
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Host", style="green")
        table.add_column("Database", style="yellow")

        for ds in config.datasources:
            table.add_row(
                ds.id,
                ds.type,
                ds.connection.host,
                ds.connection.database
            )

        console.print(table)

    # Ontology objects
    if config.ontology.objects:
        table = Table(title="Ontology Objects", box=box.ROUNDED)
        table.add_column("Name", style="cyan")
        table.add_column("Table", style="magenta")
        table.add_column("Datasource", style="green")
        table.add_column("Properties", style="yellow")

        for obj in config.ontology.objects:
            table.add_row(
                obj.name,
                obj.table,
                obj.datasource,
                str(len(obj.properties))
            )

        console.print(table)


def format_ontology(ontology: dict[str, OntologyObject]) -> None:
    """Format ontology with Rich tables.

    Args:
        ontology: Dictionary mapping object names to OntologyObject instances
    """
    console.print(f"\n[bold]Discovered {len(ontology)} ontology objects[/bold]\n")

    for name, obj in ontology.items():
        table = Table(title=f"Object: {name}", box=box.ROUNDED)
        table.add_column("Property", style="cyan")
        table.add_column("Column", style="magenta")

        # Add properties
        for prop_name, col_name in obj.properties.items():
            table.add_row(prop_name, col_name)

        console.print(table)


def format_ontology_object(obj: OntologyObject) -> None:
    """Format a single ontology object with Rich.

    Args:
        obj: OntologyObject to format
    """
    console.print(Panel(
        f"[bold]Table:[/bold] {obj.table.name}",
        title=f"Object: {obj.name}",
        border_style="blue"
    ))

    table = Table(box=box.ROUNDED)
    table.add_column("Property", style="cyan")
    table.add_column("Column", style="magenta")

    # Add properties
    for prop_name, col_name in obj.properties.items():
        table.add_row(prop_name, col_name)

    console.print(table)


def format_query_result(result: dict) -> None:
    """Format query result with Rich.

    Args:
        result: Query result dictionary containing sql, results, and answer
    """
    # Display SQL query
    if "sql" in result and result["sql"]:
        console.print("\n[bold]Generated SQL:[/bold]")
        syntax = Syntax(result["sql"], "sql", theme="monokai", line_numbers=False)
        console.print(syntax)

    # Display results
    if "results" in result and result["results"]:
        console.print("\n[bold]Query Results:[/bold]")

        # Create table from results
        if isinstance(result["results"], list) and len(result["results"]) > 0:
            first_row = result["results"][0]
            if isinstance(first_row, dict):
                table = Table(box=box.ROUNDED)

                # Add columns
                for key in first_row.keys():
                    table.add_column(str(key), style="cyan")

                # Add rows (limit to first 10)
                for row in result["results"][:10]:
                    table.add_row(*[str(v) for v in row.values()])

                console.print(table)

                if len(result["results"]) > 10:
                    console.print(f"\n[dim]... and {len(result['results']) - 10} more rows[/dim]")

    # Display answer
    if "answer" in result and result["answer"]:
        console.print("\n[bold green]Answer:[/bold green]")
        console.print(Panel(result["answer"], border_style="green"))
