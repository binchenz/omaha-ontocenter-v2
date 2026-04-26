"""Backward-compat shim. Real implementation lives at app.services.agent.chat_service."""
from app.services.agent.chat_service import (  # noqa: F401
    ChatService,
    _json_dumps,
    openai,
    anthropic,
    OmahaService,
    semantic_service,
    ChartEngine,
    OntologyStore,
    format_onboarding_context,
)
