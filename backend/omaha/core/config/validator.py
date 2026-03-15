"""Configuration validator that checks config against the live database."""

from dataclasses import dataclass, field

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError

from omaha.core.config.schema import DataSourceConfig, OntologyObjectConfig, RootConfig
from omaha.utils.exceptions import ConfigValidationError


@dataclass
class ValidationResult:
    """Result of a full configuration validation run."""

    is_valid: bool
    errors: list[str]
    warnings: list[str] = field(default_factory=list)


def _build_url(datasource: DataSourceConfig) -> str:
    """Build a SQLAlchemy connection URL from a DataSourceConfig."""
    conn = datasource.connection
    password = conn.password.get_secret_value()
    return (
        f"postgresql+psycopg2://{conn.user}:{password}"
        f"@{conn.host}:{conn.port}/{conn.database}"
    )


def validate_datasource(datasource: DataSourceConfig) -> list[str]:
    """Try to connect to the database and return a list of error strings.

    An empty list means the datasource is reachable and credentials are valid.
    """
    errors: list[str] = []
    url = _build_url(datasource)
    try:
        engine = create_engine(url, connect_args={"connect_timeout": 10})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        errors.append(
            f"Datasource '{datasource.id}': cannot connect to "
            f"{datasource.connection.host}:{datasource.connection.port} — {exc}"
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"Datasource '{datasource.id}': unexpected error while connecting — {exc}"
        )
    return errors


def validate_ontology_object(
    obj: OntologyObjectConfig, datasource: DataSourceConfig
) -> list[str]:
    """Check that the object's table and all mapped columns exist in the database.

    Returns a list of error strings; empty means everything is present.
    """
    errors: list[str] = []
    url = _build_url(datasource)
    schema = datasource.schema

    try:
        engine = create_engine(url, connect_args={"connect_timeout": 10})
        inspector = inspect(engine)

        # Check table existence
        tables = inspector.get_table_names(schema=schema)
        if obj.table not in tables:
            errors.append(
                f"Object '{obj.name}': table '{obj.table}' does not exist "
                f"in schema '{schema}' on datasource '{datasource.id}'. "
                f"Available tables: {sorted(tables)}"
            )
            # No point checking columns if the table is missing
            return errors

        # Collect existing column names
        existing_columns = {col["name"] for col in inspector.get_columns(obj.table, schema=schema)}

        # Check primary key column
        if obj.primary_key not in existing_columns:
            errors.append(
                f"Object '{obj.name}': primary key column '{obj.primary_key}' "
                f"does not exist in table '{obj.table}'."
            )

        # Check each mapped property column
        for prop in obj.properties:
            if prop.column not in existing_columns:
                errors.append(
                    f"Object '{obj.name}': property '{prop.name}' maps to column "
                    f"'{prop.column}' which does not exist in table '{obj.table}'."
                )

    except SQLAlchemyError as exc:
        errors.append(
            f"Object '{obj.name}': database introspection failed — {exc}"
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(
            f"Object '{obj.name}': unexpected error during introspection — {exc}"
        )

    return errors


def validate_config(config: RootConfig) -> ValidationResult:
    """Run all validations and return a ValidationResult.

    Validates every datasource connection and every ontology object's
    table/column mapping against the live database.
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Index datasources by id for quick lookup
    datasource_map = {ds.id: ds for ds in config.datasources}

    # Validate each datasource connection
    for ds in config.datasources:
        errors.extend(validate_datasource(ds))

    # Validate each ontology object
    for obj in config.ontology.objects:
        ds = datasource_map.get(obj.datasource)
        if ds is None:
            # Cross-reference already caught by schema; add a warning here
            warnings.append(
                f"Object '{obj.name}' references unknown datasource '{obj.datasource}'; "
                "skipping database validation."
            )
            continue
        errors.extend(validate_ontology_object(obj, ds))

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
