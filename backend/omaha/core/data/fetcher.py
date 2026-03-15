"""Data fetcher: queries the database based on ontology object config."""

import logging
from typing import Dict

import pandas as pd
from sqlalchemy import create_engine, text

from omaha.core.config.schema import DataSourceConfig, OntologyObjectConfig, RootConfig

logger = logging.getLogger(__name__)


def _build_connection_url(datasource: DataSourceConfig) -> str:
    """Build a SQLAlchemy connection URL from a DataSourceConfig."""
    conn = datasource.connection
    password = conn.password.get_secret_value()
    return (
        f"postgresql+psycopg2://{conn.user}:{password}"
        f"@{conn.host}:{conn.port}/{conn.database}"
    )


def _build_select_sql(obj: OntologyObjectConfig, schema: str) -> str:
    """Build a SELECT statement for the given ontology object."""
    columns = ", ".join(prop.column for prop in obj.properties)
    return f"SELECT {columns} FROM {schema}.{obj.table}"


def fetch_ontology_object(
    obj: OntologyObjectConfig,
    datasource: DataSourceConfig,
) -> pd.DataFrame:
    """Fetch data for a single ontology object and return a mapped DataFrame.

    Column names in the returned DataFrame use property names (not raw DB column names).
    Returns an empty DataFrame with correct columns when the query yields no rows.
    Raises RuntimeError on connection or query failures.
    """
    logger.info("Fetching object '%s' from table '%s'", obj.name, obj.table)

    try:
        engine = create_engine(_build_connection_url(datasource))
    except Exception as exc:
        raise RuntimeError(
            f"Failed to create database engine for datasource '{datasource.id}': {exc}"
        ) from exc

    sql = _build_select_sql(obj, datasource.schema)
    logger.debug("Executing SQL: %s", sql)

    try:
        with engine.connect() as conn:
            raw_df: pd.DataFrame = pd.read_sql(text(sql), conn)
    except Exception as exc:
        raise RuntimeError(
            f"Query failed for object '{obj.name}': {exc}"
        ) from exc

    # Build column rename map: db_column -> property_name
    rename_map = {prop.column: prop.name for prop in obj.properties}
    result = raw_df.rename(columns=rename_map)

    # Ensure all property columns are present (handles empty results correctly)
    expected_columns = [prop.name for prop in obj.properties]
    for col in expected_columns:
        if col not in result.columns:
            result[col] = pd.Series(dtype=object)

    return result[expected_columns]


def fetch_all_objects(config: RootConfig) -> Dict[str, pd.DataFrame]:
    """Fetch all ontology objects defined in config.

    Returns a dict mapping object name to its DataFrame.
    Objects referencing unknown datasources are skipped with a warning.
    """
    datasource_map = {ds.id: ds for ds in config.datasources}
    results: Dict[str, pd.DataFrame] = {}

    for obj in config.ontology.objects:
        if obj.datasource not in datasource_map:
            logger.warning(
                "Skipping object '%s': unknown datasource '%s'",
                obj.name,
                obj.datasource,
            )
            continue

        datasource = datasource_map[obj.datasource]
        logger.info("Fetching object '%s'", obj.name)
        results[obj.name] = fetch_ontology_object(obj, datasource)

    return results
