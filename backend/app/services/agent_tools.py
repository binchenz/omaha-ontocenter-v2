"""Backward-compat shim. Real implementation lives at app.services.agent.toolkit."""
from app.services.agent.toolkit import (  # noqa: F401
    AgentToolkit,
    _summarize_dataframe,
    OntologyImporter,
    OntologyStore,
)
