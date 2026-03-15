"""LangGraph workflow for agent."""

from typing import Any, Dict

from langgraph.graph import END, StateGraph

from omaha.core.agent.nodes import (
    execute_query,
    format_response,
    handle_error,
    generate_sql,
    plan_query,
)
from omaha.core.agent.state import AgentState
from omaha.core.config.schema import RootConfig
from omaha.core.ontology.models import OntologyObject
from omaha.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_agent_graph(
    config: RootConfig, ontology: Dict[str, OntologyObject], llm: Any
) -> StateGraph:
    """Create the LangGraph workflow.

    Args:
        config: Root configuration
        ontology: Dictionary of ontology objects
        llm: LLM instance

    Returns:
        Compiled StateGraph
    """
    # Create graph
    workflow = StateGraph(AgentState)

    # Add nodes with partial application of config/ontology/llm
    workflow.add_node("plan", lambda state: plan_query(state, config, ontology))
    workflow.add_node("generate_sql", lambda state: generate_sql(state, config, llm))
    workflow.add_node("execute", lambda state: execute_query(state, config))
    workflow.add_node("format", lambda state: format_response(state, llm))
    workflow.add_node("handle_error", lambda state: handle_error(state))

    # Define edges
    workflow.set_entry_point("plan")

    # After planning, generate SQL
    workflow.add_edge("plan", "generate_sql")

    # After SQL generation, check for errors
    def check_sql_error(state: AgentState) -> str:
        """Route based on whether SQL generation had errors."""
        if state.get("error"):
            return "handle_error"
        return "execute"

    workflow.add_conditional_edges("generate_sql", check_sql_error, {"handle_error": "handle_error", "execute": "execute"})

    # After execution, check for errors
    def check_execution_error(state: AgentState) -> str:
        """Route based on whether execution had errors."""
        if state.get("error"):
            return "handle_error"
        return "format"

    workflow.add_conditional_edges("execute", check_execution_error, {"handle_error": "handle_error", "format": "format"})

    # After formatting, end
    workflow.add_edge("format", END)

    # After error handling, end
    workflow.add_edge("handle_error", END)

    # Compile graph
    return workflow.compile()


def run_query(
    question: str,
    config: RootConfig,
    ontology: Dict[str, OntologyObject],
    llm_provider: str = "openai"
) -> Dict[str, Any]:
    """Run a natural language query through the agent.

    Args:
        question: Natural language question
        config: Root configuration
        ontology: Dictionary of ontology objects
        llm_provider: LLM provider name (openai, anthropic, or deepseek)

    Returns:
        Dictionary containing the final state with response or error
    """
    from omaha.core.agent.llm_factory import create_llm

    # Create LLM instance
    llm = create_llm(llm_provider)
    logger.info("Running query", question=question)

    # Create initial state
    initial_state: AgentState = {
        "question": question,
        "ontology_context": "",
        "sql_query": None,
        "results": None,
        "formatted_response": None,
        "error": None,
    }

    # Create and run graph
    graph = create_agent_graph(config, ontology, llm)
    final_state = graph.invoke(initial_state)

    logger.info("Query complete", has_error=bool(final_state.get("error")))

    return final_state
