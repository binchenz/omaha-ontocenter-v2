"""Agent workflow nodes."""

import json
import re
from typing import Any, Dict

import pandas as pd
import sqlparse
from sqlparse.sql import Statement

from omaha.core.agent.prompts import RESPONSE_FORMATTING_PROMPT, SQL_GENERATION_PROMPT
from omaha.core.agent.state import AgentState
from omaha.core.config.schema import RootConfig
from omaha.core.data.connectors import create_connector
from omaha.core.ontology.models import OntologyObject
from omaha.utils.exceptions import AgentError, QueryError
from omaha.utils.logger import setup_logger

logger = setup_logger(__name__)


def plan_query(
    state: AgentState, config: RootConfig, ontology: Dict[str, OntologyObject]
) -> AgentState:
    """Analyze question and identify relevant ontology objects.

    Args:
        state: Current agent state
        config: Root configuration
        ontology: Dictionary of ontology objects

    Returns:
        Updated agent state with ontology_context
    """
    question = state["question"].lower()
    logger.info("Planning query", question=state["question"])

    # Identify relevant ontology objects based on keywords
    relevant_objects = []
    for obj_name, obj in ontology.items():
        # Check if object name appears in question (with word boundaries)
        if re.search(r'\b' + re.escape(obj_name.lower()) + r'\b', question):
            relevant_objects.append(obj)
            continue

        # Check if any property names appear in question
        for prop_name in obj.properties.keys():
            prop_pattern = re.escape(prop_name.lower().replace("_", " "))
            if re.search(r'\b' + prop_pattern + r'\b', question):
                relevant_objects.append(obj)
                break

    # Build ontology context
    context_parts = []
    for obj in relevant_objects:
        context_parts.append(f"Object: {obj.name}")
        context_parts.append(f"Table: {obj.table.name}")
        context_parts.append("Columns:")
        for col in obj.table.columns:
            context_parts.append(
                f"  - {col.name} ({col.type}, {'nullable' if col.nullable else 'not null'})"
            )
        context_parts.append("Properties:")
        for prop_name, col_name in obj.properties.items():
            context_parts.append(f"  - {prop_name} -> {col_name}")
        context_parts.append("")

    ontology_context = "\n".join(context_parts)

    if not ontology_context:
        # If no specific objects found, include all objects
        logger.warning("No specific objects found, including all ontology objects")
        for obj in ontology.values():
            context_parts.append(f"Object: {obj.name}")
            context_parts.append(f"Table: {obj.table.name}")
            context_parts.append("Columns:")
            for col in obj.table.columns:
                context_parts.append(
                    f"  - {col.name} ({col.type}, {'nullable' if col.nullable else 'not null'})"
                )
            context_parts.append("")
        ontology_context = "\n".join(context_parts)

    logger.info("Query planning complete", objects_found=len(relevant_objects))

    return {
        **state,
        "ontology_context": ontology_context,
    }


def generate_sql(state: AgentState, config: RootConfig, llm: Any) -> AgentState:
    """Generate SQL query from question and ontology context.

    Args:
        state: Current agent state
        config: Root configuration
        llm: LLM instance

    Returns:
        Updated agent state with sql_query
    """
    logger.info("Generating SQL query")

    # Format prompt
    prompt = SQL_GENERATION_PROMPT.format(
        question=state["question"], ontology_context=state["ontology_context"]
    )

    try:
        # Call LLM
        response = llm.invoke(prompt)

        # Extract SQL from response
        if hasattr(response, "content"):
            sql_query = response.content.strip()
        else:
            sql_query = str(response).strip()

        # Clean up SQL query (remove markdown code blocks if present)
        if sql_query.startswith("```sql"):
            sql_query = sql_query[6:]
        if sql_query.startswith("```"):
            sql_query = sql_query[3:]
        if sql_query.endswith("```"):
            sql_query = sql_query[:-3]
        sql_query = sql_query.strip()

        # Validate SQL
        _validate_sql(sql_query)

        logger.info("SQL query generated", query=sql_query)

        return {
            **state,
            "sql_query": sql_query,
        }

    except Exception as e:
        logger.error("Failed to generate SQL", error=str(e))
        return {
            **state,
            "error": f"Failed to generate SQL query: {str(e)}",
        }


def execute_query(state: AgentState, config: RootConfig) -> AgentState:
    """Execute SQL query and return results.

    Args:
        state: Current agent state
        config: Root configuration

    Returns:
        Updated agent state with results
    """
    if not state["sql_query"]:
        return {
            **state,
            "error": "No SQL query to execute",
        }

    logger.info("Executing SQL query", query=state["sql_query"])

    try:
        # Validate SQL query for safety
        _validate_sql(state["sql_query"])

        # Get the first datasource (MVP assumes single datasource)
        if not config.datasources:
            raise AgentError("No datasources configured")

        datasource_config = config.datasources[0]

        # Create connector and execute query
        connector = create_connector(datasource_config)
        with connector:
            df = connector.execute_query(state["sql_query"])

        # Convert DataFrame to dict for easier handling
        if df.empty:
            results = {"rows": [], "count": 0}
        else:
            # Limit result size to prevent memory issues
            max_rows = 1000
            if len(df) > max_rows:
                logger.warning(f"Result set truncated to {max_rows} rows", total_rows=len(df))
                df = df.head(max_rows)

            results = {
                "rows": df.to_dict(orient="records"),
                "count": len(df),
                "columns": list(df.columns),
            }

        logger.info("Query executed successfully", row_count=results["count"])

        return {
            **state,
            "results": results,
        }

    except Exception as e:
        logger.error("Failed to execute query", error=str(e))
        return {
            **state,
            "error": f"Failed to execute query: {str(e)}",
        }


def format_response(state: AgentState, llm: Any) -> AgentState:
    """Format results into natural language response.

    Args:
        state: Current agent state
        llm: LLM instance

    Returns:
        Updated agent state with formatted_response
    """
    if state["results"] is None:
        return {
            **state,
            "error": "No results to format",
        }

    logger.info("Formatting response")

    try:
        # Format results for prompt
        results_str = json.dumps(state["results"], indent=2, default=str)

        # Format prompt
        prompt = RESPONSE_FORMATTING_PROMPT.format(
            question=state["question"],
            sql_query=state["sql_query"],
            results=results_str,
        )

        # Call LLM
        response = llm.invoke(prompt)

        # Extract formatted response
        if hasattr(response, "content"):
            formatted_response = response.content.strip()
        else:
            formatted_response = str(response).strip()

        logger.info("Response formatted successfully")

        return {
            **state,
            "formatted_response": formatted_response,
        }

    except Exception as e:
        logger.error("Failed to format response", error=str(e))
        return {
            **state,
            "error": f"Failed to format response: {str(e)}",
        }


def handle_error(state: AgentState) -> AgentState:
    """Handle errors in the workflow.

    Args:
        state: Current agent state

    Returns:
        Updated agent state with formatted error message
    """
    logger.error("Handling workflow error", error=state.get("error"))

    error_message = state.get("error", "Unknown error occurred")

    # Differentiate error types for better user feedback
    if "QueryError" in error_message or "execute query" in error_message.lower():
        formatted_error = f"I encountered a database error: {error_message}"
    elif "AgentError" in error_message or "SQL" in error_message:
        formatted_error = f"I encountered an issue processing your request: {error_message}"
    elif "generate SQL" in error_message.lower():
        formatted_error = f"I had trouble understanding your question: {error_message}"
    elif "format response" in error_message.lower():
        formatted_error = f"I retrieved the data but had trouble formatting it: {error_message}"
    else:
        formatted_error = f"I encountered an error: {error_message}"

    return {
        **state,
        "formatted_response": formatted_error,
    }


def _validate_sql(sql_query: str) -> None:
    """Validate SQL query for safety.

    Args:
        sql_query: SQL query to validate

    Raises:
        AgentError: If SQL query is invalid or unsafe
    """
    if not sql_query:
        raise AgentError("SQL query is empty")

    # Check for SQL injection patterns using regex
    injection_patterns = [
        (r'--', "SQL comment detected"),
        (r'/\*', "SQL comment detected"),
        (r'\*/', "SQL comment detected"),
        (r';', "Multiple statements not allowed (semicolon detected)"),
        (r'\bUNION\b', "UNION attack detected"),
        (r'\bxp_\w+', "SQL Server extended procedure detected"),
        (r'\bsp_\w+', "SQL Server stored procedure detected"),
    ]

    for pattern, error_msg in injection_patterns:
        if re.search(pattern, sql_query, re.IGNORECASE):
            raise AgentError(error_msg)

    # Parse SQL
    try:
        parsed = sqlparse.parse(sql_query)
    except Exception as e:
        raise AgentError(f"Failed to parse SQL: {str(e)}")

    if not parsed:
        raise AgentError("No SQL statements found")

    # Check for multiple statements
    if len(parsed) > 1:
        raise AgentError("Multiple SQL statements not allowed")

    statement: Statement = parsed[0]

    # Get statement type
    stmt_type = statement.get_type()

    # Only allow SELECT statements
    if stmt_type != "SELECT":
        raise AgentError(f"Only SELECT statements allowed, got {stmt_type}")

    logger.debug("SQL validation passed", query=sql_query)
