"""Agent state definition for LangGraph workflow."""

from typing import Optional, TypedDict


class AgentState(TypedDict):
    """State for the agent workflow."""

    question: str
    ontology_context: Optional[str]
    sql_query: Optional[str]
    results: Optional[dict]
    formatted_response: Optional[str]
    error: Optional[str]
